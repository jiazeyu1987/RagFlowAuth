from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_equipment_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "equipment_assets"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_assets (
                equipment_id TEXT PRIMARY KEY,
                asset_code TEXT NOT NULL UNIQUE,
                equipment_name TEXT NOT NULL,
                manufacturer TEXT,
                model TEXT,
                serial_number TEXT,
                location TEXT,
                supplier_name TEXT,
                owner_user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                purchase_date TEXT,
                acceptance_date TEXT,
                commissioning_date TEXT,
                retirement_due_date TEXT,
                retired_date TEXT,
                next_metrology_due_date TEXT,
                next_maintenance_due_date TEXT,
                notes TEXT,
                reminder_sent_at_ms INTEGER,
                reminder_sent_for_due_date TEXT,
                created_by_user_id TEXT NOT NULL,
                updated_by_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "equipment_assets", "asset_code TEXT")
    add_column_if_missing(conn, "equipment_assets", "equipment_name TEXT")
    add_column_if_missing(conn, "equipment_assets", "manufacturer TEXT")
    add_column_if_missing(conn, "equipment_assets", "model TEXT")
    add_column_if_missing(conn, "equipment_assets", "serial_number TEXT")
    add_column_if_missing(conn, "equipment_assets", "location TEXT")
    add_column_if_missing(conn, "equipment_assets", "supplier_name TEXT")
    add_column_if_missing(conn, "equipment_assets", "owner_user_id TEXT")
    add_column_if_missing(conn, "equipment_assets", "status TEXT")
    add_column_if_missing(conn, "equipment_assets", "purchase_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "acceptance_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "commissioning_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "retirement_due_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "retired_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "next_metrology_due_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "next_maintenance_due_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "notes TEXT")
    add_column_if_missing(conn, "equipment_assets", "reminder_sent_at_ms INTEGER")
    add_column_if_missing(conn, "equipment_assets", "reminder_sent_for_due_date TEXT")
    add_column_if_missing(conn, "equipment_assets", "created_by_user_id TEXT")
    add_column_if_missing(conn, "equipment_assets", "updated_by_user_id TEXT")
    add_column_if_missing(conn, "equipment_assets", "created_at_ms INTEGER")
    add_column_if_missing(conn, "equipment_assets", "updated_at_ms INTEGER")

    if not table_exists(conn, "equipment_asset_status_history"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_asset_status_history (
                transition_id TEXT PRIMARY KEY,
                equipment_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                action TEXT NOT NULL,
                notes TEXT,
                actor_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "equipment_asset_status_history", "equipment_id TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "from_status TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "to_status TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "action TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "notes TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "actor_user_id TEXT")
    add_column_if_missing(conn, "equipment_asset_status_history", "created_at_ms INTEGER")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_equipment_assets_asset_code ON equipment_assets(asset_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_equipment_assets_status ON equipment_assets(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_equipment_assets_owner_updated "
        "ON equipment_assets(owner_user_id, updated_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_equipment_status_history_equipment_time "
        "ON equipment_asset_status_history(equipment_id, created_at_ms ASC)"
    )
