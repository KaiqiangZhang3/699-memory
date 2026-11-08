def create(client, title="Write report", description=""):
    resp = client.request("POST", "/tasks", {"title": title, "description": description})
    assert resp.status == 201, resp.body
    return resp.body


def test_create_and_list_own_tasks(client_for):
    alice = client_for("alice")
    task = create(alice, "Write report", "Q4 numbers")
    assert task["status"] == "todo"
    assert task["title"] == "Write report"
    assert task["created_at"] == task["updated_at"] == "2026-11-01T12:00:00+00:00"
    assert [t["id"] for t in alice.request("GET", "/tasks").body["tasks"]] == [task["id"]]


def test_title_is_required(client_for):
    alice = client_for("alice")
    assert alice.request("POST", "/tasks", {"title": "   "}).status == 400
    assert alice.request("POST", "/tasks", {}).status == 400


def test_members_only_see_their_own_tasks(client_for):
    alice, bob = client_for("alice"), client_for("bob")
    create(alice, "Alice task")
    create(bob, "Bob task")
    assert [t["title"] for t in bob.request("GET", "/tasks").body["tasks"]] == ["Bob task"]


def test_admin_sees_all_tasks(client_for):
    create(client_for("alice"), "Alice task")
    create(client_for("bob"), "Bob task")
    titles = [t["title"] for t in client_for("admin").request("GET", "/tasks").body["tasks"]]
    assert titles == ["Alice task", "Bob task"]


def test_member_cannot_read_someone_elses_task(client_for):
    task = create(client_for("alice"))
    assert client_for("bob").request("GET", f"/tasks/{task['id']}").status == 403


def test_owner_can_update_status(client_for):
    alice = client_for("alice")
    task = create(alice)
    resp = alice.request("PATCH", f"/tasks/{task['id']}", {"status": "doing"})
    assert resp.status == 200
    assert resp.body["status"] == "doing"


def test_invalid_status_rejected(client_for):
    alice = client_for("alice")
    task = create(alice)
    assert alice.request("PATCH", f"/tasks/{task['id']}", {"status": "blocked"}).status == 400


def test_unknown_field_rejected(client_for):
    alice = client_for("alice")
    task = create(alice)
    assert alice.request("PATCH", f"/tasks/{task['id']}", {"owner_id": 2}).status == 400


def test_owner_can_delete(client_for):
    alice = client_for("alice")
    task = create(alice)
    assert alice.request("DELETE", f"/tasks/{task['id']}").status == 204
    assert alice.request("GET", f"/tasks/{task['id']}").status == 404


def test_member_cannot_delete_someone_elses_task(client_for):
    task = create(client_for("alice"))
    assert client_for("bob").request("DELETE", f"/tasks/{task['id']}").status == 403


def test_admin_can_delete_any_task(client_for):
    task = create(client_for("alice"))
    assert client_for("admin").request("DELETE", f"/tasks/{task['id']}").status == 204


def test_missing_task_is_404(client_for):
    assert client_for("alice").request("GET", "/tasks/999").status == 404


def test_unknown_route_is_404(client_for):
    assert client_for("alice").request("GET", "/nope").status == 404


def test_wrong_method_is_405(client_for):
    assert client_for("alice").request("PUT", "/tasks").status == 405
