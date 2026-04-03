from __future__ import annotations

import sqlite3
import time

from .helpers import add_column_if_missing, table_exists


DEFAULT_WATERMARK_POLICY_ID = "default-controlled-watermark"
DEFAULT_WATERMARK_TEMPLATE = "用户:{username} | 公司:{company} | 时间:{timestamp} | 用途:{purpose} | 文档ID:{doc_id}"
DEFAULT_WATERMARK_LABEL = "受控预览"
DEFAULT_WATERMARK_COLOR = "#6b7280"


def ensure_watermark_policy_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "watermark_policies"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watermark_policies (
                policy_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                text_template TEXT NOT NULL,
                label_text TEXT NOT NULL,
                text_color TEXT NOT NULL,
                opacity REAL NOT NULL DEFAULT 0.18,
                rotation_deg INTEGER NOT NULL DEFAULT -24,
                gap_x INTEGER NOT NULL DEFAULT 260,
                gap_y INTEGER NOT NULL DEFAULT 180,
                font_size INTEGER NOT NULL DEFAULT 18,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "watermark_policies", "name TEXT")
    add_column_if_missing(conn, "watermark_policies", "text_template TEXT")
    add_column_if_missing(conn, "watermark_policies", "label_text TEXT")
    add_column_if_missing(conn, "watermark_policies", "text_color TEXT NOT NULL DEFAULT '#6b7280'")
    add_column_if_missing(conn, "watermark_policies", "opacity REAL NOT NULL DEFAULT 0.18")
    add_column_if_missing(conn, "watermark_policies", "rotation_deg INTEGER NOT NULL DEFAULT -24")
    add_column_if_missing(conn, "watermark_policies", "gap_x INTEGER NOT NULL DEFAULT 260")
    add_column_if_missing(conn, "watermark_policies", "gap_y INTEGER NOT NULL DEFAULT 180")
    add_column_if_missing(conn, "watermark_policies", "font_size INTEGER NOT NULL DEFAULT 18")
    add_column_if_missing(conn, "watermark_policies", "is_active INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "watermark_policies", "created_at_ms INTEGER")
    add_column_if_missing(conn, "watermark_policies", "updated_at_ms INTEGER")

    _seed_default_watermark_policy(conn)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watermark_policies_active ON watermark_policies(is_active)")


def _seed_default_watermark_policy(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT policy_id FROM watermark_policies WHERE is_active = 1 LIMIT 1").fetchone()
    if row:
        return

    now_ms = int(time.time() * 1000)
    conn.execute(
        """
        INSERT OR REPLACE INTO watermark_policies (
            policy_id,
            name,
            text_template,
            label_text,
            text_color,
            opacity,
            rotation_deg,
            gap_x,
            gap_y,
            font_size,
            is_active,
            created_at_ms,
            updated_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            DEFAULT_WATERMARK_POLICY_ID,
            "默认受控预览水印策略",
            DEFAULT_WATERMARK_TEMPLATE,
            DEFAULT_WATERMARK_LABEL,
            DEFAULT_WATERMARK_COLOR,
            0.18,
            -24,
            260,
            180,
            18,
            now_ms,
            now_ms,
        ),
    )
