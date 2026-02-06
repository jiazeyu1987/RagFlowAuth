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


def ensure_audit_events_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "audit_events"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                actor_username TEXT,
                company_id INTEGER,
                company_name TEXT,
                department_id INTEGER,
                department_name TEXT,
                created_at_ms INTEGER NOT NULL,
                source TEXT,
                doc_id TEXT,
                filename TEXT,
                kb_id TEXT,
                kb_dataset_id TEXT,
                kb_name TEXT,
                meta_json TEXT
            )
            """
        )

    add_column_if_missing(conn, "audit_events", "actor_username TEXT")
    add_column_if_missing(conn, "audit_events", "company_id INTEGER")
    add_column_if_missing(conn, "audit_events", "company_name TEXT")
    add_column_if_missing(conn, "audit_events", "department_id INTEGER")
    add_column_if_missing(conn, "audit_events", "department_name TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_time ON audit_events(created_at_ms)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events(action)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_actor ON audit_events(actor)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_actor_username ON audit_events(actor_username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_company_id ON audit_events(company_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_department_id ON audit_events(department_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_kb ON audit_events(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_kb_dataset_id ON audit_events(kb_dataset_id)")

    # Best-effort backfill from directory tables for existing rows (helps filtering immediately).
    try:
        if table_exists(conn, "users"):
            conn.execute(
                """
                UPDATE audit_events
                SET actor_username = (
                    SELECT u.username FROM users u WHERE u.user_id = audit_events.actor
                )
                WHERE (actor_username IS NULL OR actor_username = '')
                  AND actor IS NOT NULL AND actor != ''
                """
            )
            conn.execute(
                """
                UPDATE audit_events
                SET company_id = (
                    SELECT u.company_id FROM users u WHERE u.user_id = audit_events.actor
                )
                WHERE company_id IS NULL
                  AND actor IS NOT NULL AND actor != ''
                """
            )
            conn.execute(
                """
                UPDATE audit_events
                SET department_id = (
                    SELECT u.department_id FROM users u WHERE u.user_id = audit_events.actor
                )
                WHERE department_id IS NULL
                  AND actor IS NOT NULL AND actor != ''
                """
            )
        if table_exists(conn, "companies"):
            conn.execute(
                """
                UPDATE audit_events
                SET company_name = (
                    SELECT c.name FROM companies c WHERE c.company_id = audit_events.company_id
                )
                WHERE (company_name IS NULL OR company_name = '')
                  AND company_id IS NOT NULL
                """
            )
        if table_exists(conn, "departments"):
            conn.execute(
                """
                UPDATE audit_events
                SET department_name = (
                    SELECT d.name FROM departments d WHERE d.department_id = audit_events.department_id
                )
                WHERE (department_name IS NULL OR department_name = '')
                  AND department_id IS NOT NULL
                """
            )
        conn.commit()
    except Exception:
        pass
