from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_quality_system_positions_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "quality_system_positions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_system_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                in_signoff INTEGER NOT NULL DEFAULT 0,
                in_compiler INTEGER NOT NULL DEFAULT 0,
                in_approver INTEGER NOT NULL DEFAULT 0,
                seeded_from_json INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_system_positions_name ON quality_system_positions(name)"
    )


def ensure_quality_system_position_assignments_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "quality_system_position_assignments"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_system_position_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                FOREIGN KEY(position_id) REFERENCES quality_system_positions(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_system_position_assignments_position_user
        ON quality_system_position_assignments(position_id, user_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quality_system_position_assignments_user
        ON quality_system_position_assignments(user_id)
        """
    )


def ensure_quality_system_file_categories_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "quality_system_file_categories"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_system_file_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                seeded_from_json INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_system_file_categories_name ON quality_system_file_categories(name)"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_quality_system_file_categories_active
        ON quality_system_file_categories(is_active, updated_at_ms DESC)
        """
    )


def ensure_quality_system_config_tables(conn: sqlite3.Connection) -> None:
    ensure_quality_system_positions_table(conn)
    ensure_quality_system_position_assignments_table(conn)
    ensure_quality_system_file_categories_table(conn)
