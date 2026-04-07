from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Optional, List, Set

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite

from .models import User
from .password import hash_password, verify_password


DEFAULT_CREDENTIAL_FAILURE_LIMIT = 5
DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS = 15 * 60 * 1000
DEFAULT_CREDENTIAL_LOCKOUT_MS = 15 * 60 * 1000


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
                       manager_user_id,
                       max_login_sessions, idle_timeout_minutes, can_change_password,
                       disable_login_enabled, disable_login_until_ms,
                       electronic_signature_enabled,
                       created_at_ms, last_login_at_ms, created_by, full_name, managed_kb_root_node_id,
                       password_changed_at_ms, credential_fail_count, credential_fail_window_started_at_ms,
                       credential_locked_until_ms, employee_user_id
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
                    full_name=row[19],
                    manager_user_id=row[9],
                    employee_user_id=(str(row[25]).strip() if row[25] is not None and str(row[25]).strip() else None),
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    max_login_sessions=int(row[10] or 3),
                    idle_timeout_minutes=int(row[11] or 120),
                    can_change_password=bool(row[12]) if row[12] is not None else True,
                    disable_login_enabled=bool(row[13]) if row[13] is not None else False,
                    disable_login_until_ms=int(row[14]) if row[14] is not None else None,
                    electronic_signature_enabled=bool(row[15]) if row[15] is not None else True,
                    created_at_ms=row[16],
                    last_login_at_ms=row[17],
                    created_by=row[18],
                    managed_kb_root_node_id=row[20],
                    password_changed_at_ms=(int(row[21]) if row[21] is not None else None),
                    credential_fail_count=int(row[22] or 0),
                    credential_fail_window_started_at_ms=(int(row[23]) if row[23] is not None else None),
                    credential_locked_until_ms=(int(row[24]) if row[24] is not None else None),
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
                       manager_user_id,
                       max_login_sessions, idle_timeout_minutes, can_change_password,
                       disable_login_enabled, disable_login_until_ms,
                       electronic_signature_enabled,
                       created_at_ms, last_login_at_ms, created_by, full_name, managed_kb_root_node_id,
                       password_changed_at_ms, credential_fail_count, credential_fail_window_started_at_ms,
                       credential_locked_until_ms, employee_user_id
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
                    full_name=row[19],
                    manager_user_id=row[9],
                    employee_user_id=(str(row[25]).strip() if row[25] is not None and str(row[25]).strip() else None),
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    max_login_sessions=int(row[10] or 3),
                    idle_timeout_minutes=int(row[11] or 120),
                    can_change_password=bool(row[12]) if row[12] is not None else True,
                    disable_login_enabled=bool(row[13]) if row[13] is not None else False,
                    disable_login_until_ms=int(row[14]) if row[14] is not None else None,
                    electronic_signature_enabled=bool(row[15]) if row[15] is not None else True,
                    created_at_ms=row[16],
                    last_login_at_ms=row[17],
                    created_by=row[18],
                    managed_kb_root_node_id=row[20],
                    password_changed_at_ms=(int(row[21]) if row[21] is not None else None),
                    credential_fail_count=int(row[22] or 0),
                    credential_fail_window_started_at_ms=(int(row[23]) if row[23] is not None else None),
                    credential_locked_until_ms=(int(row[24]) if row[24] is not None else None),
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
            cursor.execute(
                f"""
                SELECT user_id, username
                FROM users
                WHERE user_id IN ({placeholders}) OR username IN ({placeholders})
                """,
                ids + ids,
            )
            rows = cursor.fetchall()
            result: dict[str, str] = {}
            for row in rows:
                if not row or len(row) < 2:
                    continue
                user_id = str(row[0] or "")
                username = str(row[1] or "")
                if user_id:
                    result[user_id] = username
                if username:
                    result[username] = username
            return result
        finally:
            conn.close()

    def get_display_names_by_ids(self, user_ids: Set[str]) -> dict[str, str]:
        ids = [i for i in (user_ids or set()) if isinstance(i, str) and i]
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
            rows = cursor.fetchall()
            result: dict[str, str] = {}
            for row in rows:
                if not row or len(row) < 3:
                    continue
                user_id = str(row[0] or "")
                username = str(row[1] or "")
                full_name = str(row[2] or "").strip()
                display_name = full_name or username
                if not display_name:
                    continue
                if user_id:
                    result[user_id] = display_name
                if username:
                    result[username] = display_name
            return result
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
        password_hash_value = hash_password(new_password)
        self.update_password_hash(user_id, password_hash_value)

    def update_password_hash(self, user_id: str, password_hash_value: str):
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute(
                    """
                    INSERT INTO password_history (user_id, password_hash, created_at_ms)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, str(row[0]), now_ms),
                )
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?,
                    password_changed_at_ms = ?,
                    credential_fail_count = 0,
                    credential_fail_window_started_at_ms = NULL,
                    credential_locked_until_ms = NULL
                WHERE user_id = ?
                """,
                (password_hash_value, now_ms, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_credential_failures(self, user_id: str) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE users
                SET credential_fail_count = 0,
                    credential_fail_window_started_at_ms = NULL,
                    credential_locked_until_ms = NULL
                WHERE user_id = ?
                """,
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def record_credential_failure(
        self,
        user_id: str,
        *,
        now_ms: int | None = None,
        max_failures: int = DEFAULT_CREDENTIAL_FAILURE_LIMIT,
        window_ms: int = DEFAULT_CREDENTIAL_FAILURE_WINDOW_MS,
        lockout_ms: int = DEFAULT_CREDENTIAL_LOCKOUT_MS,
    ) -> tuple[int | None, bool]:
        current_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT credential_fail_count, credential_fail_window_started_at_ms, credential_locked_until_ms
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None, False

            previous_count = int(row[0] or 0)
            previous_window_start = int(row[1]) if row[1] is not None else None
            previous_locked_until = int(row[2]) if row[2] is not None else None

            if previous_locked_until is not None and current_ms < previous_locked_until:
                conn.commit()
                return previous_locked_until, False

            if previous_window_start is None or current_ms - previous_window_start > int(window_ms):
                next_count = 1
                next_window_start = current_ms
            else:
                next_count = previous_count + 1
                next_window_start = previous_window_start

            next_locked_until = None
            newly_locked = False
            if next_count >= int(max_failures):
                next_locked_until = current_ms + int(lockout_ms)
                newly_locked = True

            conn.execute(
                """
                UPDATE users
                SET credential_fail_count = ?,
                    credential_fail_window_started_at_ms = ?,
                    credential_locked_until_ms = ?
                WHERE user_id = ?
                """,
                (next_count, next_window_start, next_locked_until, user_id),
            )
            conn.commit()
            return next_locked_until, newly_locked
        finally:
            conn.close()

    def password_matches_recent_history(self, user_id: str, password: str, *, limit: int = 5) -> bool:
        user = self.get_by_user_id(user_id)
        if user is None:
            return False
        ok, _ = verify_password(password, user.password_hash)
        if ok:
            return True

        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT password_hash
                FROM password_history
                WHERE user_id = ?
                ORDER BY created_at_ms DESC, id DESC
                LIMIT ?
                """,
                (user_id, int(max(1, limit))),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            stored_hash = str(row[0] or "")
            matched, _ = verify_password(password, stored_hash)
            if matched:
                return True
        return False

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
                SELECT user_id, username, password_hash, email, role, group_id, company_id, department_id, status,
                       manager_user_id,
                       max_login_sessions, idle_timeout_minutes, can_change_password,
                       disable_login_enabled, disable_login_until_ms,
                       electronic_signature_enabled,
                       created_at_ms, last_login_at_ms, created_by, full_name, managed_kb_root_node_id,
                       password_changed_at_ms, credential_fail_count, credential_fail_window_started_at_ms,
                       credential_locked_until_ms, employee_user_id
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
                user = User(
                    user_id=row[0],
                    username=row[1],
                    password_hash=row[2],
                    email=row[3],
                    full_name=row[19],
                    manager_user_id=row[9],
                    employee_user_id=(str(row[25]).strip() if row[25] is not None and str(row[25]).strip() else None),
                    role=row[4],
                    group_id=row[5],
                    company_id=row[6],
                    department_id=row[7],
                    status=row[8],
                    max_login_sessions=int(row[10] or 3),
                    idle_timeout_minutes=int(row[11] or 120),
                    can_change_password=bool(row[12]) if row[12] is not None else True,
                    disable_login_enabled=bool(row[13]) if row[13] is not None else False,
                    disable_login_until_ms=int(row[14]) if row[14] is not None else None,
                    electronic_signature_enabled=bool(row[15]) if row[15] is not None else True,
                    created_at_ms=row[16],
                    last_login_at_ms=row[17],
                    created_by=row[18],
                    managed_kb_root_node_id=row[20],
                    password_changed_at_ms=(int(row[21]) if row[21] is not None else None),
                    credential_fail_count=int(row[22] or 0),
                    credential_fail_window_started_at_ms=(int(row[23]) if row[23] is not None else None),
                    credential_locked_until_ms=(int(row[24]) if row[24] is not None else None),
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
