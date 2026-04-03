from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, columns, table_exists


def ensure_users_group_id_column(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    cols = columns(conn, "users")
    if "group_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN group_id INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)")


def ensure_users_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "users"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            manager_user_id TEXT,
            role TEXT NOT NULL DEFAULT 'viewer',
            group_id INTEGER,
            company_id INTEGER,
            department_id INTEGER,
            max_login_sessions INTEGER NOT NULL DEFAULT 3,
            idle_timeout_minutes INTEGER NOT NULL DEFAULT 120,
            status TEXT NOT NULL DEFAULT 'active',
            can_change_password INTEGER NOT NULL DEFAULT 1,
            disable_login_enabled INTEGER NOT NULL DEFAULT 0,
            disable_login_until_ms INTEGER,
            electronic_signature_enabled INTEGER NOT NULL DEFAULT 1,
            password_changed_at_ms INTEGER,
            credential_fail_count INTEGER NOT NULL DEFAULT 0,
            credential_fail_window_started_at_ms INTEGER,
            credential_locked_until_ms INTEGER,
            created_at_ms INTEGER NOT NULL,
            last_login_at_ms INTEGER,
            created_by TEXT,
            full_name TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_manager_user_id ON users(manager_user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id)")


def ensure_org_columns_on_users(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "manager_user_id TEXT")
    add_column_if_missing(conn, "users", "company_id INTEGER")
    add_column_if_missing(conn, "users", "department_id INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_manager_user_id ON users(manager_user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id)")


def ensure_user_login_policy_columns(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "max_login_sessions INTEGER NOT NULL DEFAULT 3")
    add_column_if_missing(conn, "users", "idle_timeout_minutes INTEGER NOT NULL DEFAULT 120")
    add_column_if_missing(conn, "users", "can_change_password INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "users", "disable_login_enabled INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "users", "disable_login_until_ms INTEGER")


def ensure_user_full_name_column(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "full_name TEXT")


def ensure_user_managed_kb_root_column(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "managed_kb_root_node_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_managed_kb_root_node_id ON users(managed_kb_root_node_id)")


def ensure_user_password_security_columns(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "password_changed_at_ms INTEGER")
    add_column_if_missing(conn, "users", "credential_fail_count INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "users", "credential_fail_window_started_at_ms INTEGER")
    add_column_if_missing(conn, "users", "credential_locked_until_ms INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_credential_locked_until_ms ON users(credential_locked_until_ms)")


def ensure_user_electronic_signature_columns(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "electronic_signature_enabled INTEGER NOT NULL DEFAULT 1")


def ensure_password_history_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at_ms INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_password_history_user_created ON password_history(user_id, created_at_ms DESC)")
