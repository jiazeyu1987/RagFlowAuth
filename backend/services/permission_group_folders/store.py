from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Any

from backend.database.sqlite import connect_sqlite

_UNSET = object()


class PermissionGroupFolderStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect_sqlite(self._db_path)

    def list_folders(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT folder_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                FROM permission_group_folders
                ORDER BY COALESCE(parent_id, ''), name COLLATE NOCASE, created_at_ms
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def get_folder(self, folder_id: str) -> dict[str, Any] | None:
        if not isinstance(folder_id, str) or not folder_id:
            return None
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT folder_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                FROM permission_group_folders
                WHERE folder_id = ?
                """,
                (folder_id,),
            ).fetchone()
            return dict(row) if row else None

    def create_folder(self, name: str, parent_id: str | None, *, created_by: str | None = None) -> dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("missing_name")
        clean_parent = str(parent_id).strip() if isinstance(parent_id, str) and parent_id.strip() else None
        now_ms = int(time.time() * 1000)
        folder_id = str(uuid.uuid4())
        with self._conn() as conn:
            if clean_parent:
                parent = conn.execute(
                    "SELECT folder_id FROM permission_group_folders WHERE folder_id = ?",
                    (clean_parent,),
                ).fetchone()
                if not parent:
                    raise ValueError("parent_not_found")
            try:
                conn.execute(
                    """
                    INSERT INTO permission_group_folders (
                        folder_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (folder_id, clean_name, clean_parent, created_by, now_ms, now_ms),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("duplicate_name") from exc
        out = self.get_folder(folder_id)
        if not out:
            raise ValueError("create_failed")
        return out

    def update_folder(
        self,
        folder_id: str,
        *,
        name: str | None | object = _UNSET,
        parent_id: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        if not isinstance(folder_id, str) or not folder_id:
            raise ValueError("missing_folder_id")
        with self._conn() as conn:
            current = conn.execute(
                """
                SELECT folder_id, name, parent_id
                FROM permission_group_folders
                WHERE folder_id = ?
                """,
                (folder_id,),
            ).fetchone()
            if not current:
                raise ValueError("folder_not_found")
            next_name = str(name).strip() if isinstance(name, str) else current["name"]
            if not next_name:
                raise ValueError("missing_name")
            if parent_id is _UNSET:
                next_parent = current["parent_id"]
            elif parent_id is None:
                next_parent = None
            else:
                next_parent = str(parent_id).strip() or None
            if next_parent == folder_id:
                raise ValueError("invalid_parent")
            if next_parent:
                parent = conn.execute(
                    "SELECT folder_id FROM permission_group_folders WHERE folder_id = ?",
                    (next_parent,),
                ).fetchone()
                if not parent:
                    raise ValueError("parent_not_found")
                descendants = self._expand_folder_ids_with_conn(conn, [folder_id])
                if next_parent in descendants:
                    raise ValueError("invalid_parent")
            now_ms = int(time.time() * 1000)
            try:
                conn.execute(
                    """
                    UPDATE permission_group_folders
                    SET name = ?, parent_id = ?, updated_at_ms = ?
                    WHERE folder_id = ?
                    """,
                    (next_name, next_parent, now_ms, folder_id),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("duplicate_name") from exc
        updated = self.get_folder(folder_id)
        if not updated:
            raise ValueError("update_failed")
        return updated

    def delete_folder(self, folder_id: str) -> bool:
        if not isinstance(folder_id, str) or not folder_id:
            return False
        with self._conn() as conn:
            child = conn.execute(
                "SELECT folder_id FROM permission_group_folders WHERE parent_id = ? LIMIT 1",
                (folder_id,),
            ).fetchone()
            if child:
                raise ValueError("has_children")
            grouped = conn.execute(
                "SELECT group_id FROM permission_groups WHERE folder_id = ? LIMIT 1",
                (folder_id,),
            ).fetchone()
            if grouped:
                raise ValueError("has_groups")
            cur = conn.execute(
                "DELETE FROM permission_group_folders WHERE folder_id = ?",
                (folder_id,),
            )
            conn.commit()
            return bool(cur.rowcount)

    def folder_exists(self, folder_id: str | None) -> bool:
        if folder_id is None:
            return True
        clean = str(folder_id).strip() if isinstance(folder_id, str) else ""
        if not clean:
            return True
        with self._conn() as conn:
            row = conn.execute(
                "SELECT folder_id FROM permission_group_folders WHERE folder_id = ?",
                (clean,),
            ).fetchone()
            return bool(row)

    def expand_folder_ids(self, folder_ids: list[str] | set[str] | tuple[str, ...]) -> set[str]:
        clean_ids = [str(folder_id).strip() for folder_id in folder_ids if isinstance(folder_id, str) and folder_id.strip()]
        if not clean_ids:
            return set()
        with self._conn() as conn:
            return self._expand_folder_ids_with_conn(conn, clean_ids)

    def _expand_folder_ids_with_conn(self, conn: sqlite3.Connection, folder_ids: list[str]) -> set[str]:
        remaining = set(folder_ids)
        visited: set[str] = set()
        while remaining:
            current = remaining.pop()
            if current in visited:
                continue
            visited.add(current)
            cur = conn.execute(
                "SELECT folder_id FROM permission_group_folders WHERE parent_id = ?",
                (current,),
            )
            for row in cur.fetchall():
                child_id = str(row["folder_id"])
                if child_id and child_id not in visited:
                    remaining.add(child_id)
        return visited
