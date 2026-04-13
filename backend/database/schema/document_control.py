from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_document_control_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "controlled_documents"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS controlled_documents (
                controlled_document_id TEXT PRIMARY KEY,
                doc_code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                document_type TEXT NOT NULL,
                product_name TEXT,
                registration_ref TEXT,
                target_kb_id TEXT NOT NULL,
                target_kb_name TEXT,
                current_revision_id TEXT,
                effective_revision_id TEXT,
                created_by TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "controlled_documents", "doc_code TEXT")
    add_column_if_missing(conn, "controlled_documents", "title TEXT")
    add_column_if_missing(conn, "controlled_documents", "document_type TEXT")
    add_column_if_missing(conn, "controlled_documents", "product_name TEXT")
    add_column_if_missing(conn, "controlled_documents", "registration_ref TEXT")
    add_column_if_missing(conn, "controlled_documents", "target_kb_id TEXT")
    add_column_if_missing(conn, "controlled_documents", "target_kb_name TEXT")
    add_column_if_missing(conn, "controlled_documents", "current_revision_id TEXT")
    add_column_if_missing(conn, "controlled_documents", "effective_revision_id TEXT")
    add_column_if_missing(conn, "controlled_documents", "created_by TEXT")
    add_column_if_missing(conn, "controlled_documents", "created_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_documents", "updated_at_ms INTEGER")

    if not table_exists(conn, "controlled_revisions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS controlled_revisions (
                controlled_revision_id TEXT PRIMARY KEY,
                controlled_document_id TEXT NOT NULL,
                kb_doc_id TEXT NOT NULL UNIQUE,
                revision_no INTEGER NOT NULL,
                status TEXT NOT NULL,
                change_summary TEXT,
                previous_revision_id TEXT,
                approved_by TEXT,
                approved_at_ms INTEGER,
                effective_at_ms INTEGER,
                obsolete_at_ms INTEGER,
                created_by TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "controlled_revisions", "controlled_document_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "kb_doc_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "revision_no INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "status TEXT")
    add_column_if_missing(conn, "controlled_revisions", "change_summary TEXT")
    add_column_if_missing(conn, "controlled_revisions", "previous_revision_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approved_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "effective_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "created_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "created_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "updated_at_ms INTEGER")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_controlled_documents_doc_code ON controlled_documents(doc_code)")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_controlled_revisions_doc_revision_no
        ON controlled_revisions(controlled_document_id, revision_no)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_controlled_revisions_one_effective
        ON controlled_revisions(controlled_document_id)
        WHERE status = 'effective'
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_documents_target_kb
        ON controlled_documents(target_kb_id, target_kb_name)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_documents_updated_at
        ON controlled_documents(updated_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_revisions_status
        ON controlled_revisions(status, updated_at_ms DESC)
        """
    )
