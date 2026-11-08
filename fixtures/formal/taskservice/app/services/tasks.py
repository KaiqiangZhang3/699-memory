"""Task operations and access rules.

Members see and change only their own tasks. Admins can see and change all tasks.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

STATUSES = ("todo", "doing", "done")
EDITABLE_FIELDS = ("title", "description", "status")


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class ValidationError(Exception):
    pass


class TaskService:
    def __init__(self, conn: sqlite3.Connection, clock: Callable[[], str]) -> None:
        self.conn = conn
        self.clock = clock

    # -- queries ---------------------------------------------------------

    def list_for(self, user: dict) -> list[dict]:
        if user["role"] == "admin":
            rows = self.conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM tasks WHERE owner_id = ? ORDER BY id", (user["id"],)).fetchall()
        return [dict(r) for r in rows]

    def get(self, user: dict, task_id: int) -> dict:
        task = self._fetch(task_id)
        self._check_access(user, task)
        return task

    # -- commands --------------------------------------------------------

    def create(self, user: dict, title: str, description: str = "") -> dict:
        title = self._clean_title(title)
        now = self.clock()
        cur = self.conn.execute(
            "INSERT INTO tasks (owner_id, title, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, 'todo', ?, ?)",
            (user["id"], title, description or "", now, now),
        )
        self.conn.commit()
        return self._fetch(int(cur.lastrowid))

    def update(self, user: dict, task_id: int, changes: dict) -> dict:
        task = self._fetch(task_id)
        unknown = set(changes) - set(EDITABLE_FIELDS)
        if unknown:
            raise ValidationError(f"cannot change field(s): {', '.join(sorted(unknown))}")
        if not changes:
            raise ValidationError("no changes given")
        if "title" in changes:
            changes["title"] = self._clean_title(changes["title"])
        if "status" in changes and changes["status"] not in STATUSES:
            raise ValidationError(f"status must be one of {', '.join(STATUSES)}")
        assignments = ", ".join(f"{field} = ?" for field in changes)
        self.conn.execute(
            f"UPDATE tasks SET {assignments}, updated_at = ? WHERE id = ?",
            (*changes.values(), self.clock(), task["id"]),
        )
        self.conn.commit()
        return self._fetch(task_id)

    def delete(self, user: dict, task_id: int) -> None:
        task = self._fetch(task_id)
        self._check_access(user, task)
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    # -- helpers ---------------------------------------------------------

    def _fetch(self, task_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise NotFound(f"task {task_id} not found")
        return dict(row)

    @staticmethod
    def _check_access(user: dict, task: dict) -> None:
        if user["role"] != "admin" and task["owner_id"] != user["id"]:
            raise Forbidden("not your task")

    @staticmethod
    def _clean_title(title: object) -> str:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("title is required")
        if len(title) > 200:
            raise ValidationError("title is too long")
        return title.strip()
