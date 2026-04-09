from __future__ import annotations

import time
from typing import Callable


class UserToolPermissionStore:
    def __init__(
        self,
        *,
        connection_factory: Callable[[], object],
        now_ms_factory: Callable[[], int] | None = None,
    ) -> None:
        self._connection_factory = connection_factory
        self._now_ms_factory = now_ms_factory or (lambda: int(time.time() * 1000))

    def list_tool_ids(self, user_id: str, *, conn=None) -> list[str]:
        def _query(active_conn) -> list[str]:
            cursor = active_conn.cursor()
            cursor.execute(
                """
                SELECT tool_id
                FROM user_tool_permissions
                WHERE user_id = ?
                ORDER BY tool_id
                """,
                (user_id,),
            )
            return [str(row[0]) for row in cursor.fetchall() if row and row[0]]

        if conn is not None:
            return _query(conn)

        owned_conn = self._connection_factory()
        try:
            return _query(owned_conn)
        finally:
            owned_conn.close()

    def replace_tool_ids(
        self,
        user_id: str,
        tool_ids: list[str],
        *,
        granted_by_user_id: str | None = None,
        conn=None,
    ) -> bool:
        clean_granted_by = str(granted_by_user_id or "").strip() or None
        now_ms = self._now_ms_factory()

        def _replace(active_conn) -> bool:
            cursor = active_conn.cursor()
            cursor.execute("DELETE FROM user_tool_permissions WHERE user_id = ?", (user_id,))
            for tool_id in tool_ids:
                clean_tool_id = str(tool_id or "").strip()
                if not clean_tool_id:
                    continue
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO user_tool_permissions (
                        user_id, tool_id, granted_by_user_id, created_at_ms, updated_at_ms
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, clean_tool_id, clean_granted_by, now_ms, now_ms),
                )
            return True

        if conn is not None:
            return _replace(conn)

        owned_conn = self._connection_factory()
        try:
            result = _replace(owned_conn)
            owned_conn.commit()
            return result
        finally:
            owned_conn.close()

    def list_managed_viewer_user_ids(self, manager_user_id: str, *, conn=None) -> list[str]:
        clean_manager_user_id = str(manager_user_id or "").strip()
        if not clean_manager_user_id:
            return []

        def _query(active_conn) -> list[str]:
            cursor = active_conn.cursor()
            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE manager_user_id = ?
                  AND role = 'viewer'
                ORDER BY created_at_ms DESC
                """,
                (clean_manager_user_id,),
            )
            return [str(row[0]) for row in cursor.fetchall() if row and row[0]]

        if conn is not None:
            return _query(conn)

        owned_conn = self._connection_factory()
        try:
            return _query(owned_conn)
        finally:
            owned_conn.close()
