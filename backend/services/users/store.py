from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Optional, List, Set

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .credential_store import (
    DEFAULT_CREDENTIAL_FAILURE_LIMIT,
    DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS,
    DEFAULT_CREDENTIAL_LOCKOUT_MS,
    UserCredentialStore,
)
from .group_membership_store import UserPermissionGroupStore
from .models import User
from .password import hash_password
from .store_support import (
    USER_READ_COLUMNS,
    build_display_name_reference_map,
    build_user_from_row,
    build_username_reference_map,
    normalize_lookup_ids,
)
USER_LOOKUP_QUERIES = {
    "username": f"SELECT {USER_READ_COLUMNS} FROM users WHERE username = ?",
    "user_id": f"SELECT {USER_READ_COLUMNS} FROM users WHERE user_id = ?",
}


class UserStore:
    def __init__(self, db_path: str = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._credential_store = UserCredentialStore(connection_factory=self._get_connection)
        self._group_membership_store = UserPermissionGroupStore(connection_factory=self._get_connection)

    def _get_connection(self):
        return connect_sqlite(self.db_path)

    def _fetch_user_by(self, query_key: str, value: str) -> Optional[User]:
        query = USER_LOOKUP_QUERIES[query_key]
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, (value,))
            row = cursor.fetchone()
            if row is None:
                return None

            group_ids = self._get_user_group_ids(str(row[0]), conn)
            return build_user_from_row(row, group_ids=group_ids)
        finally:
            conn.close()

    def get_by_username(self, username: str) -> Optional[User]:
        return self._fetch_user_by("username", username)

    def get_by_user_id(self, user_id: str) -> Optional[User]:
        return self._fetch_user_by("user_id", user_id)

    def get_usernames_by_ids(self, user_ids: Set[str]) -> dict[str, str]:
        ids = normalize_lookup_ids(user_ids)
        if not ids:
            return {}
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(
                f"""
                SELECT user_id, username
                FROM users
                WHERE user_id IN ({placeholders}) OR username IN ({placeholders})
                """,
                ids + ids,
            )
            return build_username_reference_map(cursor.fetchall())
        finally:
            conn.close()

    def get_display_names_by_ids(self, user_ids: Set[str]) -> dict[str, str]:
        ids = normalize_lookup_ids(user_ids)
        if not ids:
            return {}
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(
                f"""
                SELECT user_id, username, full_name
                FROM users
                WHERE user_id IN ({placeholders}) OR username IN ({placeholders})
                """,
                ids + ids,
            )
            return build_display_name_reference_map(cursor.fetchall())
        finally:
            conn.close()

    def _get_user_group_ids(self, user_id: str, conn) -> List[int]:
        return self._group_membership_store.list_group_ids(user_id, conn=conn)

    def create_user(
        self,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        manager_user_id: Optional[str] = None,
        company_id: Optional[int] = None,
        department_id: Optional[int] = None,
        role: str = "viewer",
        group_id: Optional[int] = None,
        status: str = "active",
        max_login_sessions: int = 3,
        idle_timeout_minutes: int = 120,
        can_change_password: bool = True,
        disable_login_enabled: bool = False,
        disable_login_until_ms: Optional[int] = None,
        created_by: Optional[str] = None,
        managed_kb_root_node_id: Optional[str] = None,
        electronic_signature_enabled: bool = True,
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
                    user_id, username, password_hash, email, manager_user_id, role, group_id, company_id, department_id,
                    max_login_sessions, idle_timeout_minutes, status,
                    can_change_password, disable_login_enabled, disable_login_until_ms,
                    electronic_signature_enabled,
                    password_changed_at_ms,
                    credential_fail_count, credential_fail_window_started_at_ms, credential_locked_until_ms,
                    created_at_ms, created_by, full_name, managed_kb_root_node_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    password_hash_value,
                    email,
                    manager_user_id,
                    role,
                    group_id,
                    company_id,
                    department_id,
                    int(max_login_sessions),
                    int(idle_timeout_minutes),
                    status,
                    1 if can_change_password else 0,
                    1 if disable_login_enabled else 0,
                    int(disable_login_until_ms) if disable_login_until_ms is not None else None,
                    1 if electronic_signature_enabled else 0,
                    now_ms,
                    0,
                    None,
                    None,
                    now_ms,
                    created_by,
                    full_name,
                    managed_kb_root_node_id,
                ),
            )
            conn.commit()
            return User(
                user_id=user_id,
                username=username,
                password_hash=password_hash_value,
                email=email,
                full_name=full_name,
                manager_user_id=manager_user_id,
                employee_user_id=None,
                role=role,
                group_id=group_id,
                company_id=company_id,
                department_id=department_id,
                max_login_sessions=int(max_login_sessions),
                idle_timeout_minutes=int(idle_timeout_minutes),
                status=status,
                can_change_password=bool(can_change_password),
                disable_login_enabled=bool(disable_login_enabled),
                disable_login_until_ms=int(disable_login_until_ms) if disable_login_until_ms is not None else None,
                electronic_signature_enabled=bool(electronic_signature_enabled),
                password_changed_at_ms=now_ms,
                credential_fail_count=0,
                credential_fail_window_started_at_ms=None,
                credential_locked_until_ms=None,
                created_at_ms=now_ms,
                created_by=created_by,
                managed_kb_root_node_id=managed_kb_root_node_id,
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        finally:
            conn.close()

    def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        manager_user_id: Optional[str] = None,
        company_id: Optional[int] = None,
        department_id: Optional[int] = None,
        role: Optional[str] = None,
        group_id: Optional[int] = None,
        status: Optional[str] = None,
        max_login_sessions: Optional[int] = None,
        idle_timeout_minutes: Optional[int] = None,
        can_change_password: Optional[bool] = None,
        disable_login_enabled: Optional[bool] = None,
        disable_login_until_ms: Optional[int] = None,
        managed_kb_root_node_id: Optional[str] = None,
        electronic_signature_enabled: Optional[bool] = None,
    ) -> Optional[User]:
        updates = []
        params = []

        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if manager_user_id is not None:
            updates.append("manager_user_id = ?")
            params.append(str(manager_user_id).strip() or None)
        if company_id is not None:
            updates.append("company_id = ?")
            params.append(company_id)
        if department_id is not None:
            updates.append("department_id = ?")
            params.append(department_id)
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if max_login_sessions is not None:
            updates.append("max_login_sessions = ?")
            params.append(int(max_login_sessions))
        if idle_timeout_minutes is not None:
            updates.append("idle_timeout_minutes = ?")
            params.append(int(idle_timeout_minutes))
        if can_change_password is not None:
            updates.append("can_change_password = ?")
            params.append(1 if can_change_password else 0)
        if disable_login_enabled is not None:
            updates.append("disable_login_enabled = ?")
            params.append(1 if disable_login_enabled else 0)
        if disable_login_until_ms is not None:
            updates.append("disable_login_until_ms = ?")
            params.append(int(disable_login_until_ms))
        elif disable_login_enabled is not None and not disable_login_enabled:
            updates.append("disable_login_until_ms = NULL")
        if electronic_signature_enabled is not None:
            updates.append("electronic_signature_enabled = ?")
            params.append(1 if electronic_signature_enabled else 0)
        if managed_kb_root_node_id is not None:
            updates.append("managed_kb_root_node_id = ?")
            params.append(str(managed_kb_root_node_id).strip() or None)
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
        self._credential_store.update_password(user_id, new_password)

    def update_password_hash(self, user_id: str, password_hash_value: str):
        self._credential_store.update_password_hash(user_id, password_hash_value)

    def clear_credential_failures(self, user_id: str) -> None:
        self._credential_store.clear_credential_failures(user_id)

    def record_credential_failure(
        self,
        user_id: str,
        *,
        now_ms: int | None = None,
        max_failures: int = DEFAULT_CREDENTIAL_FAILURE_LIMIT,
        window_ms: int = DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS,
        lockout_ms: int = DEFAULT_CREDENTIAL_LOCKOUT_MS,
    ) -> tuple[int | None, bool]:
        return self._credential_store.record_credential_failure(
            user_id,
            now_ms=now_ms,
            max_failures=max_failures,
            window_ms=window_ms,
            lockout_ms=lockout_ms,
        )

    def password_matches_recent_history(self, user_id: str, password: str, *, limit: int = 5) -> bool:
        user = self.get_by_user_id(user_id)
        if user is None:
            return False
        return self._credential_store.password_matches_recent_history(
            user_id=user_id,
            password=password,
            current_password_hash=user.password_hash,
            limit=limit,
        )

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
        manager_user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[User]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            base_query = """
                SELECT """ + USER_READ_COLUMNS + """
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
            if manager_user_id is not None:
                base_query += " AND manager_user_id = ?"
                base_params.append(str(manager_user_id).strip() or None)
            if q:
                base_query += " AND (username LIKE ? OR full_name LIKE ?)"
                base_params.append(f"%{q}%")
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
                group_ids = self._get_user_group_ids(str(row[0]), conn)
                users.append(build_user_from_row(row, group_ids=group_ids))
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

    def sync_employee_user_ids(self, assignments: dict[str, str | None]) -> None:
        rows: list[tuple[str | None, str]] = []
        for raw_user_id, raw_employee_user_id in (assignments or {}).items():
            user_id = str(raw_user_id or "").strip()
            if not user_id:
                continue
            employee_user_id = str(raw_employee_user_id or "").strip() or None
            rows.append((employee_user_id, user_id))
        if not rows:
            return

        conn = self._get_connection()
        try:
            conn.executemany(
                """
                UPDATE users
                SET employee_user_id = ?
                WHERE user_id = ?
                """,
                rows,
            )
            conn.commit()
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
        return self._group_membership_store.replace_group_ids(user_id, group_ids)
