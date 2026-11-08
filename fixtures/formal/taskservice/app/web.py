"""WSGI application: JSON over HTTP, session cookie authentication.

Route handlers only parse requests, call auth or the service layer, and shape
responses. They do not touch the database directly.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from typing import Callable, Iterable

from . import auth
from .services import Forbidden, NotFound, TaskService, ValidationError

TASK_PATH = re.compile(r"^/tasks/(\d+)$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class HttpError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


_REASONS = {200: "OK", 201: "Created", 204: "No Content", 400: "Bad Request", 401: "Unauthorized",
            403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed"}


def make_app(conn: sqlite3.Connection, clock: Callable[[], str] = utc_now):
    tasks = TaskService(conn, clock)

    def read_json(environ) -> dict:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(length) if length else b""
        if not raw:
            return {}
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            raise HttpError(400, "body must be JSON")
        if not isinstance(body, dict):
            raise HttpError(400, "body must be a JSON object")
        return body

    def session_token(environ) -> str | None:
        cookie = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        morsel = cookie.get(auth.SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_user(environ) -> dict:
        user = auth.user_for_token(conn, session_token(environ))
        if user is None:
            raise HttpError(401, "login required")
        return user

    def route(environ) -> tuple[int, object, list[tuple[str, str]]]:
        method = environ["REQUEST_METHOD"]
        path = environ.get("PATH_INFO", "/")

        if path == "/health" and method == "GET":
            return 200, {"status": "ok"}, []

        if path == "/login" and method == "POST":
            body = read_json(environ)
            try:
                token = auth.login(conn, str(body.get("username", "")), str(body.get("password", "")), clock())
            except auth.AuthError:
                raise HttpError(401, "invalid username or password")
            user = auth.user_for_token(conn, token)
            cookie = f"{auth.SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Lax"
            return 200, {"username": user["username"], "role": user["role"]}, [("Set-Cookie", cookie)]

        if path == "/logout" and method == "POST":
            token = session_token(environ)
            if token:
                auth.logout(conn, token)
            expired = f"{auth.SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0"
            return 204, None, [("Set-Cookie", expired)]

        if path == "/tasks":
            user = current_user(environ)
            if method == "GET":
                return 200, {"tasks": tasks.list_for(user)}, []
            if method == "POST":
                body = read_json(environ)
                return 201, tasks.create(user, body.get("title"), body.get("description", "")), []
            raise HttpError(405, "method not allowed")

        match = TASK_PATH.match(path)
        if match:
            user = current_user(environ)
            task_id = int(match.group(1))
            if method == "GET":
                return 200, tasks.get(user, task_id), []
            if method == "PATCH":
                return 200, tasks.update(user, task_id, read_json(environ)), []
            if method == "DELETE":
                tasks.delete(user, task_id)
                return 204, None, []
            raise HttpError(405, "method not allowed")

        raise HttpError(404, "no such route")

    def app(environ, start_response) -> Iterable[bytes]:
        try:
            status, payload, headers = route(environ)
        except HttpError as e:
            status, payload, headers = e.status, {"error": e.message}, []
        except ValidationError as e:
            status, payload, headers = 400, {"error": str(e)}, []
        except Forbidden as e:
            status, payload, headers = 403, {"error": str(e)}, []
        except NotFound as e:
            status, payload, headers = 404, {"error": str(e)}, []
        body = b"" if payload is None else json.dumps(payload).encode()
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body))), *headers]
        start_response(f"{status} {_REASONS[status]}", headers)
        return [body]

    return app
