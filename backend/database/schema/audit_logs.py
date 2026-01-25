from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, columns, table_exists


def ensure_download_logs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "download_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            kb_dataset_id TEXT,
            kb_name TEXT,
            downloaded_by TEXT NOT NULL,
            downloaded_at_ms INTEGER NOT NULL,
            ragflow_doc_id TEXT,
            is_batch INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb ON download_logs(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb_dataset_id ON download_logs(kb_dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_time ON download_logs(downloaded_at_ms)")


def ensure_deletion_logs_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "deletion_logs"):
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deletion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            kb_dataset_id TEXT,
            kb_name TEXT,
            deleted_by TEXT NOT NULL,
            deleted_at_ms INTEGER NOT NULL,
            original_uploader TEXT,
            original_reviewer TEXT,
            ragflow_doc_id TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb ON deletion_logs(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb_dataset_id ON deletion_logs(kb_dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_time ON deletion_logs(deleted_at_ms)")


def ensure_kb_ref_columns(conn: sqlite3.Connection) -> None:
    for table_name in ("kb_documents", "deletion_logs", "download_logs"):
        if not table_exists(conn, table_name):
            continue
        add_column_if_missing(conn, table_name, "kb_dataset_id TEXT")
        add_column_if_missing(conn, table_name, "kb_name TEXT")

        existing = columns(conn, table_name)
        if "kb_id" in existing and "kb_name" in existing:
            conn.execute(f"UPDATE {table_name} SET kb_name = kb_id WHERE (kb_name IS NULL OR kb_name = '')")


def ensure_deletion_log_extended_columns(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "deletion_logs"):
        return
    add_column_if_missing(conn, "deletion_logs", "action TEXT")
    add_column_if_missing(conn, "deletion_logs", "ragflow_deleted INTEGER")
    add_column_if_missing(conn, "deletion_logs", "ragflow_delete_error TEXT")


def ensure_kb_ref_indexes(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "kb_documents"):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_dataset_id ON kb_documents(kb_dataset_id)")
    if table_exists(conn, "deletion_logs"):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deletion_logs_kb_dataset_id ON deletion_logs(kb_dataset_id)")
    if table_exists(conn, "download_logs"):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_download_logs_kb_dataset_id ON download_logs(kb_dataset_id)")

