import sqlite3
import time
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite



@dataclass
class UserKbPermission:
    id: int
    user_id: str
    kb_id: str
    granted_by: str
    granted_at_ms: int
    kb_dataset_id: Optional[str] = None
    kb_name: Optional[str] = None


class UserKbPermissionStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def grant_permission(
        self,
        user_id: str,
        kb_id: str,
        granted_by: str,
        kb_dataset_id: Optional[str] = None,
        kb_name: Optional[str] = None,
    ) -> UserKbPermission:
        """
        授予用户知识库权限
        如果权限已存在，则更新 granted_by 和 granted_at_ms
        """
        now_ms = int(time.time() * 1000)
        canonical_kb_id = kb_dataset_id or kb_id

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # 使用 INSERT OR REPLACE 处理重复
            if kb_dataset_id:
                cursor.execute(
                    """
                    DELETE FROM user_kb_permissions
                    WHERE user_id = ?
                      AND (kb_dataset_id = ? OR kb_id = ? OR kb_name = ?)
                    """,
                    (user_id, kb_dataset_id, canonical_kb_id, (kb_name or kb_id)),
                )

            cursor.execute(
                """
                INSERT INTO user_kb_permissions (user_id, kb_id, kb_dataset_id, kb_name, granted_by, granted_at_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, kb_id) DO UPDATE SET
                    kb_dataset_id = excluded.kb_dataset_id,
                    kb_name = excluded.kb_name,
                    granted_by = excluded.granted_by,
                    granted_at_ms = excluded.granted_at_ms
                """,
                (user_id, canonical_kb_id, kb_dataset_id, (kb_name or kb_id), granted_by, now_ms),
            )

            conn.commit()

            # 获取插入/更新的记录
            cursor.execute(
                """
                SELECT id, user_id, kb_id, granted_by, granted_at_ms, kb_dataset_id, kb_name
                FROM user_kb_permissions
                WHERE user_id = ? AND kb_id = ?
                """,
                (user_id, canonical_kb_id),
            )
            row = cursor.fetchone()
            return UserKbPermission(*row)
        finally:
            conn.close()

    def revoke_permission(
        self,
        user_id: str,
        kb_id: str,
        *,
        kb_refs: Optional[List[str]] = None,
        kb_dataset_id: Optional[str] = None,
    ) -> bool:
        """
        撤销用户的知识库权限
        返回是否成功撤销（如果权限不存在返回False）
        """
        refs = kb_refs or ([kb_id] if kb_id else [])
        if kb_dataset_id:
            refs = list(dict.fromkeys([*refs, kb_dataset_id]))

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    DELETE FROM user_kb_permissions
                    WHERE user_id = ?
                      AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    """,
                    [user_id, *refs, *refs, *refs],
                )
            else:
                cursor.execute(
                    "DELETE FROM user_kb_permissions WHERE user_id = ?",
                    (user_id,),
                )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_user_kbs(self, user_id: str) -> List[str]:
        """
        获取用户可访问的知识库ID列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT kb_id, kb_dataset_id FROM user_kb_permissions
                WHERE user_id = ?
                ORDER BY kb_id
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            result: list[str] = []
            for row in rows:
                if not row:
                    continue
                kb_ref = row[1] or row[0]
                if isinstance(kb_ref, str) and kb_ref:
                    result.append(kb_ref)
            return result
        finally:
            conn.close()

    def get_kb_users(self, kb_id: str, *, kb_refs: Optional[List[str]] = None) -> List[str]:
        """
        获取可访问某知识库的用户ID列表
        """
        refs = kb_refs or ([kb_id] if kb_id else [])
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    SELECT user_id FROM user_kb_permissions
                    WHERE (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    ORDER BY user_id
                    """,
                    [*refs, *refs, *refs],
                )
            else:
                cursor.execute("SELECT user_id FROM user_kb_permissions ORDER BY user_id")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            conn.close()

    def check_permission(self, user_id: str, kb_id: str, *, kb_refs: Optional[List[str]] = None) -> bool:
        """
        检查用户是否有某知识库的权限
        """
        refs = kb_refs or ([kb_id] if kb_id else [])
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM user_kb_permissions
                    WHERE user_id = ?
                      AND (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    """,
                    [user_id, *refs, *refs, *refs],
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM user_kb_permissions WHERE user_id = ?", (user_id,))
            return cursor.fetchone()[0] > 0
        finally:
            conn.close()

    def grant_batch_permissions(self, user_ids: List[str], kb_ids: List[str], granted_by: str) -> int:
        """
        批量授予多个用户多个知识库的权限
        返回授予的权限数量
        """
        now_ms = int(time.time() * 1000)
        count = 0

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            for user_id in user_ids:
                for kb_id in kb_ids:
                    cursor.execute(
                        """
                        INSERT INTO user_kb_permissions (user_id, kb_id, kb_dataset_id, kb_name, granted_by, granted_at_ms)
                        VALUES (?, ?, NULL, ?, ?, ?)
                        ON CONFLICT(user_id, kb_id) DO UPDATE SET
                            kb_name = excluded.kb_name,
                            granted_by = excluded.granted_by,
                            granted_at_ms = excluded.granted_at_ms
                        """,
                        (user_id, kb_id, kb_id, granted_by, now_ms),
                    )
                    count += 1
            conn.commit()
            return count
        finally:
            conn.close()

    def revoke_all_user_permissions(self, user_id: str) -> int:
        """
        撤销用户的所有知识库权限
        返回撤销的权限数量
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM user_kb_permissions
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def revoke_all_kb_permissions(self, kb_id: str, *, kb_refs: Optional[List[str]] = None) -> int:
        """
        撤销某知识库的所有用户权限
        返回撤销的权限数量
        """
        refs = kb_refs or ([kb_id] if kb_id else [])
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if refs:
                placeholders = ",".join("?" for _ in refs)
                cursor.execute(
                    f"""
                    DELETE FROM user_kb_permissions
                    WHERE (kb_id IN ({placeholders}) OR kb_dataset_id IN ({placeholders}) OR kb_name IN ({placeholders}))
                    """,
                    [*refs, *refs, *refs],
                )
            else:
                cursor.execute("DELETE FROM user_kb_permissions")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
