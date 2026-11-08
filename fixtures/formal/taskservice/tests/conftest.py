from __future__ import annotations

import io
import json
from dataclasses import dataclass
from http.cookies import SimpleCookie
from wsgiref.util import setup_testing_defaults

import pytest

from app.db import connect, init_db
from app.seed import SEED_USERS, seed
from app.web import make_app

FIXED_NOW = "2026-11-01T12:00:00+00:00"
PASSWORDS = {name: password for name, password, _role in SEED_USERS}


@dataclass
class Response:
    status: int
    headers: dict
    body: object


class Client:
    """Calls the WSGI app in-process and keeps cookies between requests."""

    def __init__(self, app) -> None:
        self.app = app
        self.cookies: dict[str, str] = {}

    def request(self, method: str, path: str, body: object = None) -> Response:
        raw = b"" if body is None else json.dumps(body).encode()
        environ: dict = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "wsgi.input": io.BytesIO(raw),
        })
        if self.cookies:
            environ["HTTP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())

        captured: dict = {}

        def start_response(status, headers):
            captured["status"] = int(status.split()[0])
            captured["headers"] = headers

        payload = b"".join(self.app(environ, start_response))
        for name, value in captured["headers"]:
            if name == "Set-Cookie":
                for key, morsel in SimpleCookie(value).items():
                    if morsel["max-age"] == "0":
                        self.cookies.pop(key, None)
                    else:
                        self.cookies[key] = morsel.value
        return Response(captured["status"], dict(captured["headers"]), json.loads(payload) if payload else None)

    def login(self, username: str) -> Response:
        return self.request("POST", "/login", {"username": username, "password": PASSWORDS[username]})


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_db(connection)
    seed(connection)
    yield connection
    connection.close()


@pytest.fixture
def app(conn):
    return make_app(conn, clock=lambda: FIXED_NOW)


@pytest.fixture
def client_for(app):
    """client_for("alice") returns a Client logged in as alice; client_for(None) is anonymous."""

    def make(username: str | None) -> Client:
        client = Client(app)
        if username:
            assert client.login(username).status == 200
        return client

    return make
