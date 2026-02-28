from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Any

from backend.database.sqlite import connect_sqlite


_UNSET = object()


class KnowledgeDirectoryStore:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        return connect_sqlite(self._db_path)

    def list_nodes(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT node_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                FROM kb_directory_nodes
                ORDER BY COALESCE(parent_id, ''), name COLLATE NOCASE, created_at_ms
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        if not isinstance(node_id, str) or not node_id:
            return None
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT node_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                FROM kb_directory_nodes
                WHERE node_id = ?
                """,
                (node_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def create_node(self, name: str, parent_id: str | None, *, created_by: str | None = None) -> dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("missing_name")
        clean_parent = str(parent_id).strip() if isinstance(parent_id, str) and parent_id.strip() else None
        now_ms = int(time.time() * 1000)
        node_id = str(uuid.uuid4())
        with self._conn() as conn:
            if clean_parent:
                parent = conn.execute(
                    "SELECT node_id FROM kb_directory_nodes WHERE node_id = ?",
                    (clean_parent,),
                ).fetchone()
                if not parent:
                    raise ValueError("parent_not_found")
            try:
                conn.execute(
                    """
                    INSERT INTO kb_directory_nodes (
                        node_id, name, parent_id, created_by, created_at_ms, updated_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (node_id, clean_name, clean_parent, created_by, now_ms, now_ms),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("duplicate_name") from exc
        node = self.get_node(node_id)
        if not node:
            raise ValueError("create_failed")
        return node

    def update_node(
        self,
        node_id: str,
        *,
        name: str | None | object = _UNSET,
        parent_id: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("missing_node_id")
        with self._conn() as conn:
            current = conn.execute(
                """
                SELECT node_id, name, parent_id
                FROM kb_directory_nodes
                WHERE node_id = ?
                """,
                (node_id,),
            ).fetchone()
            if not current:
                raise ValueError("node_not_found")
            next_name = str(name).strip() if isinstance(name, str) else current["name"]
            if not next_name:
                raise ValueError("missing_name")
            if parent_id is _UNSET:
                next_parent = current["parent_id"]
            elif parent_id is None:
                next_parent = None
            else:
                next_parent = str(parent_id).strip() or None
            if next_parent == node_id:
                raise ValueError("invalid_parent")
            if next_parent:
                parent = conn.execute(
                    "SELECT node_id FROM kb_directory_nodes WHERE node_id = ?",
                    (next_parent,),
                ).fetchone()
                if not parent:
                    raise ValueError("parent_not_found")
                descendants = self._expand_node_ids_with_conn(conn, [node_id])
                if next_parent in descendants:
                    raise ValueError("invalid_parent")
            now_ms = int(time.time() * 1000)
            try:
                conn.execute(
                    """
                    UPDATE kb_directory_nodes
                    SET name = ?, parent_id = ?, updated_at_ms = ?
                    WHERE node_id = ?
                    """,
                    (next_name, next_parent, now_ms, node_id),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("duplicate_name") from exc
        updated = self.get_node(node_id)
        if not updated:
            raise ValueError("update_failed")
        return updated

    def delete_node(self, node_id: str) -> bool:
        if not isinstance(node_id, str) or not node_id:
            return False
        with self._conn() as conn:
            child = conn.execute(
                "SELECT node_id FROM kb_directory_nodes WHERE parent_id = ? LIMIT 1",
                (node_id,),
            ).fetchone()
            if child:
                raise ValueError("has_children")
            bound = conn.execute(
                "SELECT dataset_id FROM kb_directory_dataset_bindings WHERE node_id = ? LIMIT 1",
                (node_id,),
            ).fetchone()
            if bound:
                raise ValueError("has_datasets")
            cur = conn.execute(
                "DELETE FROM kb_directory_nodes WHERE node_id = ?",
                (node_id,),
            )
            conn.commit()
            return bool(cur.rowcount)

    def list_bindings(self) -> dict[str, str]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT dataset_id, node_id
                FROM kb_directory_dataset_bindings
                """
            )
            return {str(row["dataset_id"]): str(row["node_id"]) for row in cur.fetchall() if row["dataset_id"] and row["node_id"]}

    def assign_dataset(self, dataset_id: str, node_id: str | None) -> None:
        clean_dataset = str(dataset_id or "").strip()
        if not clean_dataset:
            raise ValueError("missing_dataset_id")
        clean_node = str(node_id).strip() if isinstance(node_id, str) and node_id.strip() else None
        with self._conn() as conn:
            if clean_node:
                row = conn.execute(
                    "SELECT node_id FROM kb_directory_nodes WHERE node_id = ?",
                    (clean_node,),
                ).fetchone()
                if not row:
                    raise ValueError("node_not_found")
                now_ms = int(time.time() * 1000)
                conn.execute(
                    """
                    INSERT INTO kb_directory_dataset_bindings(dataset_id, node_id, updated_at_ms)
                    VALUES (?, ?, ?)
                    ON CONFLICT(dataset_id) DO UPDATE SET
                        node_id = excluded.node_id,
                        updated_at_ms = excluded.updated_at_ms
                    """,
                    (clean_dataset, clean_node, now_ms),
                )
                conn.commit()
                return
            conn.execute(
                "DELETE FROM kb_directory_dataset_bindings WHERE dataset_id = ?",
                (clean_dataset,),
            )
            conn.commit()

    def remove_bindings_for_unknown_datasets(self, known_dataset_ids: set[str]) -> int:
        if not known_dataset_ids:
            with self._conn() as conn:
                cur = conn.execute("DELETE FROM kb_directory_dataset_bindings")
                conn.commit()
                return int(cur.rowcount or 0)

        placeholders = ",".join("?" for _ in known_dataset_ids)
        with self._conn() as conn:
            cur = conn.execute(
                f"DELETE FROM kb_directory_dataset_bindings WHERE dataset_id NOT IN ({placeholders})",
                list(known_dataset_ids),
            )
            conn.commit()
            return int(cur.rowcount or 0)

    def expand_node_ids(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> set[str]:
        clean_ids = [str(node_id).strip() for node_id in node_ids if isinstance(node_id, str) and node_id.strip()]
        if not clean_ids:
            return set()
        with self._conn() as conn:
            return self._expand_node_ids_with_conn(conn, clean_ids)

    def list_dataset_ids_for_nodes(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        clean_ids = [str(node_id).strip() for node_id in node_ids if isinstance(node_id, str) and node_id.strip()]
        if not clean_ids:
            return []
        placeholders = ",".join("?" for _ in clean_ids)
        with self._conn() as conn:
            cur = conn.execute(
                f"""
                SELECT dataset_id
                FROM kb_directory_dataset_bindings
                WHERE node_id IN ({placeholders})
                ORDER BY dataset_id
                """,
                clean_ids,
            )
            return [str(row["dataset_id"]) for row in cur.fetchall() if row["dataset_id"]]

    def _expand_node_ids_with_conn(self, conn: sqlite3.Connection, node_ids: list[str]) -> set[str]:
        remaining = set(node_ids)
        visited: set[str] = set()
        while remaining:
            current = remaining.pop()
            if current in visited:
                continue
            visited.add(current)
            cur = conn.execute(
                "SELECT node_id FROM kb_directory_nodes WHERE parent_id = ?",
                (current,),
            )
            for row in cur.fetchall():
                child_id = str(row["node_id"])
                if child_id and child_id not in visited:
                    remaining.add(child_id)
        return visited
