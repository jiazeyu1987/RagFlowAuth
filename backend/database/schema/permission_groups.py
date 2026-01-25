from __future__ import annotations

import sqlite3

from .helpers import table_exists, columns


def ensure_permission_groups_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "permission_groups"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_system INTEGER DEFAULT 0,
            accessible_kbs TEXT DEFAULT '[]',
            accessible_chats TEXT DEFAULT '[]',
            can_upload INTEGER DEFAULT 0,
            can_review INTEGER DEFAULT 0,
            can_download INTEGER DEFAULT 1,
            can_delete INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def ensure_user_permission_groups_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "user_permission_groups"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_permission_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            group_id INTEGER NOT NULL,
            created_at_ms INTEGER NOT NULL,
            UNIQUE(user_id, group_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_upg_user_id ON user_permission_groups(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_upg_group_id ON user_permission_groups(group_id)")


def seed_default_permission_groups(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "permission_groups"):
        return
    cur = conn.execute("SELECT COUNT(*) FROM permission_groups")
    row = cur.fetchone()
    if not row or row[0] != 0:
        return

    conn.executemany(
        """
        INSERT INTO permission_groups (
            group_name, description, is_system,
            accessible_kbs, accessible_chats,
            can_upload, can_review, can_download, can_delete,
            created_at, updated_at
        ) VALUES (?, ?, ?, '[]', '[]', ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        [
            ("admin", "System administrator", 1, 1, 1, 1, 1),
            ("reviewer", "Document reviewer", 0, 0, 1, 1, 0),
            ("operator", "Uploader/operator", 0, 1, 0, 1, 1),
            ("viewer", "Viewer", 0, 0, 0, 1, 0),
            ("guest", "Guest", 0, 0, 0, 0, 0),
        ],
    )


def backfill_user_permission_groups_from_users_group_id(conn: sqlite3.Connection) -> None:
    """
    Final deprecation path: ensure multi-group table is the source of truth.

    If legacy users.group_id is populated, backfill it into user_permission_groups.
    Safe to call repeatedly.
    """
    if not table_exists(conn, "users") or not table_exists(conn, "user_permission_groups"):
        return
    cols = columns(conn, "users")
    if "group_id" not in cols:
        return

    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO user_permission_groups (user_id, group_id, created_at_ms)
            SELECT user_id, group_id, COALESCE(created_at_ms, 0)
            FROM users
            WHERE group_id IS NOT NULL
            """
        )
    except Exception:
        return

