from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_patent_download_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "patent_download_sessions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patent_download_sessions (
                session_id TEXT PRIMARY KEY,
                created_by TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                keyword_text TEXT,
                keywords_json TEXT,
                use_and INTEGER NOT NULL DEFAULT 1,
                sources_json TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                error TEXT,
                source_errors_json TEXT,
                source_stats_json TEXT
            )
            """
        )

    if not table_exists(conn, "patent_download_items"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patent_download_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_label TEXT NOT NULL,
                patent_id TEXT,
                title TEXT,
                abstract_text TEXT,
                publication_number TEXT,
                publication_date TEXT,
                inventor TEXT,
                assignee TEXT,
                detail_url TEXT,
                pdf_url TEXT,
                file_path TEXT,
                filename TEXT,
                file_size INTEGER,
                mime_type TEXT,
                status TEXT NOT NULL DEFAULT 'downloaded',
                error TEXT,
                analysis_text TEXT,
                analysis_file_path TEXT,
                added_doc_id TEXT,
                added_analysis_doc_id TEXT,
                ragflow_doc_id TEXT,
                added_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES patent_download_sessions(session_id)
            )
            """
        )

    # Additive migration for already-existing deployments.
    add_column_if_missing(conn, "patent_download_items", "added_doc_id TEXT")
    add_column_if_missing(conn, "patent_download_items", "added_analysis_doc_id TEXT")
    add_column_if_missing(conn, "patent_download_items", "ragflow_doc_id TEXT")
    add_column_if_missing(conn, "patent_download_items", "added_at_ms INTEGER")
    add_column_if_missing(conn, "patent_download_items", "source_label TEXT")
    add_column_if_missing(conn, "patent_download_items", "analysis_text TEXT")
    add_column_if_missing(conn, "patent_download_items", "analysis_file_path TEXT")
    add_column_if_missing(conn, "patent_download_sessions", "status TEXT")
    add_column_if_missing(conn, "patent_download_sessions", "error TEXT")
    add_column_if_missing(conn, "patent_download_sessions", "source_errors_json TEXT")
    add_column_if_missing(conn, "patent_download_sessions", "source_stats_json TEXT")
    conn.execute(
        """
        UPDATE patent_download_sessions
        SET status = 'completed'
        WHERE status IS NULL OR status = ''
        """
    )
    conn.execute(
        """
        UPDATE patent_download_sessions
        SET source_errors_json = '{}'
        WHERE source_errors_json IS NULL OR source_errors_json = ''
        """
    )
    conn.execute(
        """
        UPDATE patent_download_sessions
        SET source_stats_json = '{}'
        WHERE source_stats_json IS NULL OR source_stats_json = ''
        """
    )
    conn.execute(
        """
        UPDATE patent_download_items
        SET source_label = source
        WHERE source_label IS NULL OR source_label = ''
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_patent_download_sessions_created_by "
        "ON patent_download_sessions(created_by, created_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_patent_download_items_session "
        "ON patent_download_items(session_id, item_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_patent_download_items_status "
        "ON patent_download_items(status)"
    )
