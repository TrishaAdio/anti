"""SQLite-backed storage for sticker permits."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS permits (
    user_id    INTEGER PRIMARY KEY,
    name       TEXT,
    granted_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Permit(NamedTuple):
    user_id: int
    name: str | None
    granted_at: str


class PermitStore:
    """Tracks which DM partners are allowed to send stickers.

    The permitted ids are mirrored in memory so the sticker handler never has to
    touch the database on the hot path.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._cache = {
            int(row["user_id"]) for row in self._conn.execute("SELECT user_id FROM permits")
        }

    def __len__(self) -> int:
        return len(self._cache)

    def is_permitted(self, user_id: int) -> bool:
        return user_id in self._cache

    def grant(self, user_id: int, name: str | None = None) -> bool:
        """Permit a user. Returns True when the permit is new."""
        already = user_id in self._cache
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO permits (user_id, name) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET name = excluded.name
                """,
                (user_id, name),
            )
        self._cache.add(user_id)
        return not already

    def revoke(self, user_id: int) -> bool:
        """Remove a permit. Returns True when a permit was actually removed."""
        with self._conn:
            cursor = self._conn.execute("DELETE FROM permits WHERE user_id = ?", (user_id,))
        self._cache.discard(user_id)
        return cursor.rowcount > 0

    def all(self) -> list[Permit]:
        rows = self._conn.execute(
            "SELECT user_id, name, granted_at FROM permits ORDER BY granted_at DESC"
        )
        return [Permit(int(r["user_id"]), r["name"], r["granted_at"]) for r in rows]

    def close(self) -> None:
        self._conn.close()
