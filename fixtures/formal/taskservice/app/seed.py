"""Demo users for local development and tests. Passwords are fixture values, not real credentials."""

from __future__ import annotations

import sqlite3

from .auth import create_user

SEED_USERS = (
    ("alice", "alice-fixture-pw", "member"),
    ("bob", "bob-fixture-pw", "member"),
    ("admin", "admin-fixture-pw", "admin"),
)


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    return {name: create_user(conn, name, password, role) for name, password, role in SEED_USERS}
