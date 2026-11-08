from app.auth import hash_password, verify_password


def test_health_needs_no_login(client_for):
    assert client_for(None).request("GET", "/health").status == 200


def test_login_sets_http_only_session_cookie(client_for):
    client = client_for(None)
    resp = client.login("alice")
    assert resp.status == 200
    assert resp.body == {"username": "alice", "role": "member"}
    assert "HttpOnly" in resp.headers["Set-Cookie"]
    assert "sid" in client.cookies


def test_wrong_password_rejected(client_for):
    resp = client_for(None).request("POST", "/login", {"username": "alice", "password": "nope"})
    assert resp.status == 401


def test_unknown_user_rejected(client_for):
    resp = client_for(None).request("POST", "/login", {"username": "mallory", "password": "x"})
    assert resp.status == 401


def test_tasks_require_login(client_for):
    assert client_for(None).request("GET", "/tasks").status == 401


def test_logout_ends_session(client_for):
    client = client_for("alice")
    token = client.cookies["sid"]
    assert client.request("POST", "/logout").status == 204
    assert "sid" not in client.cookies
    client.cookies["sid"] = token  # replaying the old token must not work
    assert client.request("GET", "/tasks").status == 401


def test_password_hash_round_trip():
    stored = hash_password("s3cret")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret", stored)
    assert not verify_password("wrong", stored)


def test_invalid_json_body(client_for):
    client = client_for("alice")
    resp = client.request("POST", "/tasks", ["not", "an", "object"])
    assert resp.status == 400
