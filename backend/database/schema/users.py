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
            role TEXT NOT NULL DEFAULT 'viewer',
            group_id INTEGER,
            company_id INTEGER,
            department_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            created_at_ms INTEGER NOT NULL,
            last_login_at_ms INTEGER,
            created_by TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id)")


def ensure_org_columns_on_users(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        return
    add_column_if_missing(conn, "users", "company_id INTEGER")
    add_column_if_missing(conn, "users", "department_id INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id)")

