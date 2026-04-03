from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_kb_documents_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "kb_documents"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                uploaded_at_ms INTEGER NOT NULL,
                reviewed_by TEXT,
                reviewed_at_ms INTEGER,
                review_notes TEXT,
                ragflow_doc_id TEXT,
                kb_id TEXT NOT NULL DEFAULT '展厅',
                kb_dataset_id TEXT,
                kb_name TEXT,
                logical_doc_id TEXT,
                version_no INTEGER NOT NULL DEFAULT 1,
                previous_doc_id TEXT,
                superseded_by_doc_id TEXT,
                is_current INTEGER NOT NULL DEFAULT 1,
                effective_status TEXT,
                archived_at_ms INTEGER,
                retention_until_ms INTEGER,
                file_sha256 TEXT,
                retired_by TEXT,
                retirement_reason TEXT,
                archive_manifest_path TEXT,
                archive_package_path TEXT,
                archive_package_sha256 TEXT
            )
            """
        )

    add_column_if_missing(conn, "kb_documents", "logical_doc_id TEXT")
    add_column_if_missing(conn, "kb_documents", "version_no INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "kb_documents", "previous_doc_id TEXT")
    add_column_if_missing(conn, "kb_documents", "superseded_by_doc_id TEXT")
    add_column_if_missing(conn, "kb_documents", "is_current INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "kb_documents", "effective_status TEXT")
    add_column_if_missing(conn, "kb_documents", "archived_at_ms INTEGER")
    add_column_if_missing(conn, "kb_documents", "retention_until_ms INTEGER")
    add_column_if_missing(conn, "kb_documents", "file_sha256 TEXT")
    add_column_if_missing(conn, "kb_documents", "retired_by TEXT")
    add_column_if_missing(conn, "kb_documents", "retirement_reason TEXT")
    add_column_if_missing(conn, "kb_documents", "archive_manifest_path TEXT")
    add_column_if_missing(conn, "kb_documents", "archive_package_path TEXT")
    add_column_if_missing(conn, "kb_documents", "archive_package_sha256 TEXT")

    conn.execute(
        """
        UPDATE kb_documents
        SET logical_doc_id = doc_id
        WHERE logical_doc_id IS NULL OR TRIM(logical_doc_id) = ''
        """
    )
    conn.execute(
        """
        UPDATE kb_documents
        SET version_no = 1
        WHERE version_no IS NULL OR version_no < 1
        """
    )
    conn.execute(
        """
        UPDATE kb_documents
        SET is_current = 1
        WHERE is_current IS NULL
        """
    )
    conn.execute(
        """
        UPDATE kb_documents
        SET effective_status = status
        WHERE effective_status IS NULL OR TRIM(effective_status) = ''
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON kb_documents(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb ON kb_documents(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_dataset_id ON kb_documents(kb_dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_logical_doc_id ON kb_documents(logical_doc_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_current ON kb_documents(is_current)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_effective_status ON kb_documents(effective_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_retention_until ON kb_documents(retention_until_ms)")
