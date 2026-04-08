from __future__ import annotations

import time
from typing import Callable


class UserPermissionGroupStore:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], object],
        now_ms_factory: Callable[[], int] | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_ms_factory = now_ms_factory or (lambda: int(time.time() * 1000))

    def list_group_ids(self, user_id: str, *, conn=None) -> list[int]:
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM user_permission_groups WHERE user_id = ?", (user_id,))
            return [row[0] for row in cursor.fetchall()]

        owned_conn = self._connection_factory()
        try:
            cursor = owned_conn.cursor()
            cursor.execute("SELECT group_id FROM user_permission_groups WHERE user_id = ?", (user_id,))
            return [row[0] for row in cursor.fetchall()]
        finally:
            owned_conn.close()

    def replace_group_ids(self, user_id: str, group_ids: list[int]) -> bool:
        conn = self._connection_factory()
        cursor = conn.cursor()
        try:
            now_ms = self._now_ms_factory()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_permission_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (group_id) REFERENCES permission_groups(group_id) ON DELETE CASCADE,
                    UNIQUE(user_id, group_id)
                )
                """
            )
            cursor.execute("DELETE FROM user_permission_groups WHERE user_id = ?", (user_id,))

            for group_id_value in group_ids:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, group_id_value, now_ms),
                )

            conn.commit()
            return True
        finally:
            conn.close()
