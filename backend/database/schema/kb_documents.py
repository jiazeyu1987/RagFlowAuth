from __future__ import annotations

import sqlite3

from .helpers import table_exists


def ensure_kb_documents_table(conn: sqlite3.Connection) -> None:
    if table_exists(conn, "kb_documents"):
        return
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
            kb_name TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_status ON kb_documents(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb ON kb_documents(kb_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_kb_dataset_id ON kb_documents(kb_dataset_id)")

