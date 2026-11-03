from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import Task, utc_now


class Store:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "vision.db"
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.db:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, prompt TEXT NOT NULL, status TEXT NOT NULL,
                    route TEXT NOT NULL, risk TEXT NOT NULL, result TEXT NOT NULL,
                    error TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    subtasks TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                    message TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                    content TEXT NOT NULL, created_at TEXT NOT NULL
                );
                """
            )

    def save_task(self, task: Task) -> None:
        with self._lock, self.db:
            self.db.execute(
                """INSERT OR REPLACE INTO tasks
                (id,prompt,status,route,risk,result,error,created_at,updated_at,subtasks)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (task.id, task.prompt, task.status, task.route, task.risk, task.result,
                 task.error, task.created_at, task.updated_at, json.dumps(task.subtasks)),
            )

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._task_row(row) for row in rows]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_row(row) if row else None

    @staticmethod
    def _task_row(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["subtasks"] = json.loads(value["subtasks"])
        return value

    def event(self, kind: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {"kind": kind, "message": message, "payload": payload or {}, "created_at": utc_now()}
        with self._lock, self.db:
            cursor = self.db.execute(
                "INSERT INTO events(kind,message,payload,created_at) VALUES (?,?,?,?)",
                (kind, message, json.dumps(event["payload"]), event["created_at"]),
            )
            event["sequence"] = cursor.lastrowid
        return event

    def events(self, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.db.execute(
                "SELECT * FROM events WHERE sequence > ? ORDER BY sequence ASC LIMIT ?", (after, limit)
            ).fetchall()
        return [{"sequence": row["sequence"], "kind": row["kind"], "message": row["message"],
                 "payload": json.loads(row["payload"]), "created_at": row["created_at"]} for row in rows]

    def add_memory(self, kind: str, content: str) -> dict[str, Any]:
        with self._lock, self.db:
            cursor = self.db.execute(
                "INSERT INTO memories(kind,content,created_at) VALUES (?,?,?)", (kind, content, utc_now())
            )
            return {"id": cursor.lastrowid, "kind": kind, "content": content}

    def search_memories(self, query: str = "", limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            if query:
                rows = self.db.execute(
                    "SELECT * FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()
            else:
                rows = self.db.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.db.close()
