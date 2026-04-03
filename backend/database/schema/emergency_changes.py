from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_emergency_change_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "emergency_changes"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emergency_changes (
                change_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_by_user_id TEXT NOT NULL,
                authorizer_user_id TEXT NOT NULL,
                reviewer_user_id TEXT NOT NULL,
                authorization_basis TEXT NOT NULL,
                risk_assessment TEXT NOT NULL,
                risk_control TEXT NOT NULL,
                rollback_plan TEXT NOT NULL,
                training_notification_plan TEXT NOT NULL,
                authorization_notes TEXT,
                deployment_summary TEXT,
                impact_assessment_summary TEXT,
                post_review_summary TEXT,
                capa_actions TEXT,
                verification_summary TEXT,
                requested_at_ms INTEGER NOT NULL,
                authorized_at_ms INTEGER,
                deployed_at_ms INTEGER,
                closed_at_ms INTEGER,
                authorized_by_user_id TEXT,
                deployed_by_user_id TEXT,
                closed_by_user_id TEXT
            )
            """
        )
    add_column_if_missing(conn, "emergency_changes", "title TEXT")
    add_column_if_missing(conn, "emergency_changes", "summary TEXT")
    add_column_if_missing(conn, "emergency_changes", "status TEXT")
    add_column_if_missing(conn, "emergency_changes", "requested_by_user_id TEXT")
    add_column_if_missing(conn, "emergency_changes", "authorizer_user_id TEXT")
    add_column_if_missing(conn, "emergency_changes", "reviewer_user_id TEXT")
    add_column_if_missing(conn, "emergency_changes", "authorization_basis TEXT")
    add_column_if_missing(conn, "emergency_changes", "risk_assessment TEXT")
    add_column_if_missing(conn, "emergency_changes", "risk_control TEXT")
    add_column_if_missing(conn, "emergency_changes", "rollback_plan TEXT")
    add_column_if_missing(conn, "emergency_changes", "training_notification_plan TEXT")
    add_column_if_missing(conn, "emergency_changes", "authorization_notes TEXT")
    add_column_if_missing(conn, "emergency_changes", "deployment_summary TEXT")
    add_column_if_missing(conn, "emergency_changes", "impact_assessment_summary TEXT")
    add_column_if_missing(conn, "emergency_changes", "post_review_summary TEXT")
    add_column_if_missing(conn, "emergency_changes", "capa_actions TEXT")
    add_column_if_missing(conn, "emergency_changes", "verification_summary TEXT")
    add_column_if_missing(conn, "emergency_changes", "requested_at_ms INTEGER")
    add_column_if_missing(conn, "emergency_changes", "authorized_at_ms INTEGER")
    add_column_if_missing(conn, "emergency_changes", "deployed_at_ms INTEGER")
    add_column_if_missing(conn, "emergency_changes", "closed_at_ms INTEGER")
    add_column_if_missing(conn, "emergency_changes", "authorized_by_user_id TEXT")
    add_column_if_missing(conn, "emergency_changes", "deployed_by_user_id TEXT")
    add_column_if_missing(conn, "emergency_changes", "closed_by_user_id TEXT")

    if not table_exists(conn, "emergency_change_actions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emergency_change_actions (
                action_id TEXT PRIMARY KEY,
                change_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "emergency_change_actions", "change_id TEXT")
    add_column_if_missing(conn, "emergency_change_actions", "action TEXT")
    add_column_if_missing(conn, "emergency_change_actions", "actor_user_id TEXT")
    add_column_if_missing(conn, "emergency_change_actions", "details_json TEXT")
    add_column_if_missing(conn, "emergency_change_actions", "created_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_emergency_changes_status ON emergency_changes(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_emergency_changes_requested_at ON emergency_changes(requested_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_emergency_change_actions_change_time "
        "ON emergency_change_actions(change_id, created_at_ms)"
    )
