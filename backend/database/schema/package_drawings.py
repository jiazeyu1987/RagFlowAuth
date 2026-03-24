from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_package_drawing_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "package_drawing_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS package_drawing_records (
                model TEXT PRIMARY KEY,
                barcode TEXT,
                parameters_json TEXT NOT NULL DEFAULT '{}',
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    if not table_exists(conn, "package_drawing_images"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS package_drawing_images (
                image_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                source_type TEXT NOT NULL,
                image_url TEXT,
                rel_path TEXT,
                mime_type TEXT,
                filename TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                FOREIGN KEY(model) REFERENCES package_drawing_records(model) ON DELETE CASCADE
            )
            """
        )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_package_drawing_images_model "
        "ON package_drawing_images(model, sort_order, created_at_ms)"
    )
