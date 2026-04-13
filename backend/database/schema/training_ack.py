from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_training_ack_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "training_assignments"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS training_assignments (
                assignment_id TEXT PRIMARY KEY,
                controlled_revision_id TEXT NOT NULL,
                controlled_document_id TEXT NOT NULL,
                kb_doc_id TEXT,
                doc_code TEXT NOT NULL,
                revision_no INTEGER NOT NULL,
                assignee_user_id TEXT NOT NULL,
                assigned_by_user_id TEXT NOT NULL,
                assigned_at_ms INTEGER NOT NULL,
                min_ack_at_ms INTEGER NOT NULL,
                acknowledged_at_ms INTEGER,
                decision TEXT,
                question_thread_id TEXT,
                status TEXT NOT NULL,
                note TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                UNIQUE(controlled_revision_id, assignee_user_id)
            )
            """
        )
    add_column_if_missing(conn, "training_assignments", "controlled_revision_id TEXT")
    add_column_if_missing(conn, "training_assignments", "controlled_document_id TEXT")
    add_column_if_missing(conn, "training_assignments", "kb_doc_id TEXT")
    add_column_if_missing(conn, "training_assignments", "doc_code TEXT")
    add_column_if_missing(conn, "training_assignments", "revision_no INTEGER")
    add_column_if_missing(conn, "training_assignments", "assignee_user_id TEXT")
    add_column_if_missing(conn, "training_assignments", "assigned_by_user_id TEXT")
    add_column_if_missing(conn, "training_assignments", "assigned_at_ms INTEGER")
    add_column_if_missing(conn, "training_assignments", "min_ack_at_ms INTEGER")
    add_column_if_missing(conn, "training_assignments", "acknowledged_at_ms INTEGER")
    add_column_if_missing(conn, "training_assignments", "decision TEXT")
    add_column_if_missing(conn, "training_assignments", "question_thread_id TEXT")
    add_column_if_missing(conn, "training_assignments", "status TEXT")
    add_column_if_missing(conn, "training_assignments", "note TEXT")
    add_column_if_missing(conn, "training_assignments", "created_at_ms INTEGER")
    add_column_if_missing(conn, "training_assignments", "updated_at_ms INTEGER")

    if not table_exists(conn, "quality_question_threads"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quality_question_threads (
                thread_id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                controlled_revision_id TEXT NOT NULL,
                assignee_user_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                status TEXT NOT NULL,
                raised_at_ms INTEGER NOT NULL,
                resolved_at_ms INTEGER,
                resolver_user_id TEXT,
                resolution_text TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "quality_question_threads", "assignment_id TEXT")
    add_column_if_missing(conn, "quality_question_threads", "controlled_revision_id TEXT")
    add_column_if_missing(conn, "quality_question_threads", "assignee_user_id TEXT")
    add_column_if_missing(conn, "quality_question_threads", "question_text TEXT")
    add_column_if_missing(conn, "quality_question_threads", "status TEXT")
    add_column_if_missing(conn, "quality_question_threads", "raised_at_ms INTEGER")
    add_column_if_missing(conn, "quality_question_threads", "resolved_at_ms INTEGER")
    add_column_if_missing(conn, "quality_question_threads", "resolver_user_id TEXT")
    add_column_if_missing(conn, "quality_question_threads", "resolution_text TEXT")
    add_column_if_missing(conn, "quality_question_threads", "created_at_ms INTEGER")
    add_column_if_missing(conn, "quality_question_threads", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_assignments_user_status "
        "ON training_assignments(assignee_user_id, status, assigned_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_assignments_revision "
        "ON training_assignments(controlled_revision_id, assigned_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_quality_question_threads_status "
        "ON quality_question_threads(status, raised_at_ms DESC)"
    )
