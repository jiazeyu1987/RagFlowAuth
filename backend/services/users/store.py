from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Optional, List, Set

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .models import User
from .password import hash_password


class UserStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def get_by_username(self, username: str) -> Optional[User]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
                       created_at_ms, last_login_at_ms, created_by
                FROM users WHERE username = ?
                """,
                (username,),
            )
            row = cursor.fetchone()
            if row:
                user = User(
                    user_id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    email=row[3],
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    created_at_ms=row[9],
                    last_login_at_ms=row[10],
                    created_by=row[11],
                )
                user.group_ids = self._get_user_group_ids(user.user_id, conn)
                user.group_id = user.group_ids[0] if user.group_ids else None
                return user
            return None
        finally:
            conn.close()

    def get_by_user_id(self, user_id: str) -> Optional[User]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
                       created_at_ms, last_login_at_ms, created_by
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                user = User(
                    user_id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    email=row[3],
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    created_at_ms=row[9],
                    last_login_at_ms=row[10],
                    created_by=row[11],
                )
                user.group_ids = self._get_user_group_ids(user.user_id, conn)
                user.group_id = user.group_ids[0] if user.group_ids else None
                return user
            return None
        finally:
            conn.close()

    def get_usernames_by_ids(self, user_ids: Set[str]) -> dict[str, str]:
        ids = [i for i in (user_ids or set()) if isinstance(i, str) and i]
        if not ids:
            return {}
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(f"SELECT user_id, username FROM users WHERE user_id IN ({placeholders})", ids)
            rows = cursor.fetchall()
            return {str(r[0]): str(r[1]) for r in rows if r and len(r) >= 2}
        finally:
            conn.close()

    def _get_user_group_ids(self, user_id: str, conn) -> List[int]:
        cursor = conn.cursor()
        cursor.execute("SELECT group_id FROM user_permission_groups WHERE user_id = ?", (user_id,))
        return [row[0] for row in cursor.fetchall()]

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        company_id: Optional[int] = None,
        department_id: Optional[int] = None,
        role: str = "viewer",
        group_id: Optional[int] = None,
        status: str = "active",
        created_by: Optional[str] = None,
    ) -> User:
        # Deprecated: users.group_id is no longer the source of truth (use user_permission_groups).
        group_id = None

        user_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        password_hash_value = hash_password(password)

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (
                    user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
                    created_at_ms, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    password_hash_value,
                    email,
                    role,
                    group_id,
                    company_id,
                    department_id,
                    status,
                    now_ms,
                    created_by,
                ),
            )
            conn.commit()
            return User(
                user_id=user_id,
                username=username,
                password_hash=password_hash_value,
                email=email,
                role=role,
                group_id=group_id,
                company_id=company_id,
                department_id=department_id,
                status=status,
                created_at_ms=now_ms,
                created_by=created_by,
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        finally:
            conn.close()

    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        company_id: Optional[int] = None,
        department_id: Optional[int] = None,
        role: Optional[str] = None,
        group_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Optional[User]:
        updates = []
        params = []

        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if company_id is not None:
            updates.append("company_id = ?")
            params.append(company_id)
        if department_id is not None:
            updates.append("department_id = ?")
            params.append(department_id)
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        # Deprecated: users.group_id is no longer updated (use user_permission_groups).
        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if not updates:
            return self.get_by_user_id(user_id)

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return self.get_by_user_id(user_id)
        finally:
            conn.close()

    def update_last_login(self, user_id: str):
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET last_login_at_ms = ? WHERE user_id = ?", (now_ms, user_id))
            conn.commit()
        finally:
            conn.close()

    def update_password(self, user_id: str, new_password: str):
        password_hash_value = hash_password(new_password)
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (password_hash_value, user_id))
            conn.commit()
        finally:
            conn.close()

    def list_users(
        self,
        q: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        group_id: Optional[int] = None,
        company_id: Optional[int] = None,
        department_id: Optional[int] = None,
        created_from_ms: Optional[int] = None,
        created_to_ms: Optional[int] = None,
        limit: int = 100,
    ) -> List[User]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            base_query = """
                SELECT user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
                       created_at_ms, last_login_at_ms, created_by
                FROM users
                WHERE 1=1
            """
            base_params: list[object] = []

            if role:
                base_query += " AND role = ?"
                base_params.append(role)
            if status:
                base_query += " AND status = ?"
                base_params.append(status)
            if company_id is not None:
                base_query += " AND company_id = ?"
                base_params.append(company_id)
            if department_id is not None:
                base_query += " AND department_id = ?"
                base_params.append(department_id)
            if q:
                base_query += " AND username LIKE ?"
                base_params.append(f"%{q}%")
            if created_from_ms is not None:
                base_query += " AND created_at_ms >= ?"
                base_params.append(created_from_ms)
            if created_to_ms is not None:
                base_query += " AND created_at_ms <= ?"
                base_params.append(created_to_ms)

            query = base_query
            params: list[object] = list(base_params)

            if group_id is not None:
                query += """
                    AND (
                        EXISTS (
                            SELECT 1 FROM user_permission_groups upg
                            WHERE upg.user_id = users.user_id AND upg.group_id = ?
                        )
                    )
                """
                params.append(group_id)

            query += " ORDER BY created_at_ms DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            users: list[User] = []
            for row in rows:
                user = User(
                    user_id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    email=row[3],
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    created_at_ms=row[9],
                    last_login_at_ms=row[10],
                    created_by=row[11],
                )
                user.group_ids = self._get_user_group_ids(user.user_id, conn)
                user.group_id = user.group_ids[0] if user.group_ids else None
                users.append(user)
            return users
        finally:
            conn.close()

    def delete_user(self, user_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def count_users(self, role: Optional[str] = None, status: Optional[str] = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) FROM users WHERE 1=1"
            params = []

            if role:
                query += " AND role = ?"
                params.append(role)
            if status:
                query += " AND status = ?"
                params.append(status)

            cursor.execute(query, params)
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def set_user_permission_groups(self, user_id: str, group_ids: List[int]) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            now_ms = int(time.time() * 1000)

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

