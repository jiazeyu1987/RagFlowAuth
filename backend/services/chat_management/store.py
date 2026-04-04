from __future__ import annotations

import time

from backend.database.sqlite import connect_sqlite


class ChatOwnershipStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _get_connection(self):
        return connect_sqlite(self._db_path)

    def save_chat_owner(
        self,
        *,
        chat_id: str,
        created_by: str,
        created_at_ms: int | None = None,
    ) -> None:
        clean_chat_id = str(chat_id or "").strip()
        clean_created_by = str(created_by or "").strip()
        if not clean_chat_id:
            raise ValueError("chat_id_required")
        if not clean_created_by:
            raise ValueError("chat_owner_required")
        now_ms = int(created_at_ms) if created_at_ms is not None else int(time.time() * 1000)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chat_ownerships (
                    chat_id,
                    created_by,
                    created_at_ms
                ) VALUES (?, ?, ?)
                """,
                (clean_chat_id, clean_created_by, now_ms),
            )
            conn.commit()

    def get_chat_owner(self, chat_id: str) -> str | None:
        clean_chat_id = str(chat_id or "").strip()
        if not clean_chat_id:
            return None
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT created_by
                FROM chat_ownerships
                WHERE chat_id = ?
                """,
                (clean_chat_id,),
            ).fetchone()
        if not row:
            return None
        return str(row["created_by"] or "").strip() or None

    def list_chat_ids_by_owner(self, created_by: str) -> list[str]:
        clean_created_by = str(created_by or "").strip()
        if not clean_created_by:
            return []
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT chat_id
                FROM chat_ownerships
                WHERE created_by = ?
                ORDER BY created_at_ms DESC, chat_id ASC
                """,
                (clean_created_by,),
            ).fetchall()
        return [
            str(row["chat_id"]).strip()
            for row in rows
            if row and isinstance(row["chat_id"], str) and str(row["chat_id"]).strip()
        ]

    def delete_chat(self, chat_id: str) -> bool:
        clean_chat_id = str(chat_id or "").strip()
        if not clean_chat_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM chat_ownerships
                WHERE chat_id = ?
                """,
                (clean_chat_id,),
            )
            conn.commit()
        return bool(cursor.rowcount)
