from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_operation_approval_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "operation_approval_workflows"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_workflows (
                operation_type TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_workflows", "name TEXT")
    add_column_if_missing(conn, "operation_approval_workflows", "is_active INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "operation_approval_workflows", "created_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_workflows", "updated_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_workflow_steps"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_workflow_steps (
                workflow_step_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_workflow_steps", "operation_type TEXT")
    add_column_if_missing(conn, "operation_approval_workflow_steps", "step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_workflow_steps", "step_name TEXT")
    add_column_if_missing(conn, "operation_approval_workflow_steps", "created_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_step_approvers"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_step_approvers (
                workflow_step_approver_id TEXT PRIMARY KEY,
                workflow_step_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                approver_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_step_approvers", "workflow_step_id TEXT")
    add_column_if_missing(conn, "operation_approval_step_approvers", "operation_type TEXT")
    add_column_if_missing(conn, "operation_approval_step_approvers", "step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_step_approvers", "approver_user_id TEXT")
    add_column_if_missing(conn, "operation_approval_step_approvers", "created_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_requests"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_requests (
                request_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                status TEXT NOT NULL,
                applicant_user_id TEXT NOT NULL,
                applicant_username TEXT NOT NULL,
                target_ref TEXT,
                target_label TEXT,
                summary_json TEXT NOT NULL,
                request_payload_json TEXT NOT NULL,
                result_payload_json TEXT,
                workflow_snapshot_json TEXT NOT NULL,
                current_step_no INTEGER,
                current_step_name TEXT,
                submitted_at_ms INTEGER NOT NULL,
                completed_at_ms INTEGER,
                execution_started_at_ms INTEGER,
                executed_at_ms INTEGER,
                last_error TEXT,
                company_id INTEGER,
                department_id INTEGER
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_requests", "operation_type TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "workflow_name TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "status TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "applicant_user_id TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "applicant_username TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "target_ref TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "target_label TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "summary_json TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "request_payload_json TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "result_payload_json TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "workflow_snapshot_json TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "current_step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "current_step_name TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "submitted_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "execution_started_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "executed_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "last_error TEXT")
    add_column_if_missing(conn, "operation_approval_requests", "company_id INTEGER")
    add_column_if_missing(conn, "operation_approval_requests", "department_id INTEGER")

    if not table_exists(conn, "operation_approval_request_steps"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_request_steps (
                request_step_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                activated_at_ms INTEGER,
                completed_at_ms INTEGER
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_request_steps", "request_id TEXT")
    add_column_if_missing(conn, "operation_approval_request_steps", "step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_request_steps", "step_name TEXT")
    add_column_if_missing(conn, "operation_approval_request_steps", "status TEXT")
    add_column_if_missing(conn, "operation_approval_request_steps", "created_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_request_steps", "activated_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_request_steps", "completed_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_request_step_approvers"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_request_step_approvers (
                request_step_approver_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                request_step_id TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                approver_user_id TEXT NOT NULL,
                approver_username TEXT,
                status TEXT NOT NULL,
                action TEXT,
                notes TEXT,
                signature_id TEXT,
                acted_at_ms INTEGER
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "request_id TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "request_step_id TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "approver_user_id TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "approver_username TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "status TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "action TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "notes TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "signature_id TEXT")
    add_column_if_missing(conn, "operation_approval_request_step_approvers", "acted_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_events"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_events (
                event_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_user_id TEXT,
                actor_username TEXT,
                step_no INTEGER,
                payload_json TEXT,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_events", "request_id TEXT")
    add_column_if_missing(conn, "operation_approval_events", "event_type TEXT")
    add_column_if_missing(conn, "operation_approval_events", "actor_user_id TEXT")
    add_column_if_missing(conn, "operation_approval_events", "actor_username TEXT")
    add_column_if_missing(conn, "operation_approval_events", "step_no INTEGER")
    add_column_if_missing(conn, "operation_approval_events", "payload_json TEXT")
    add_column_if_missing(conn, "operation_approval_events", "created_at_ms INTEGER")

    if not table_exists(conn, "operation_approval_artifacts"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_approval_artifacts (
                artifact_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT,
                mime_type TEXT,
                size_bytes INTEGER,
                sha256 TEXT,
                meta_json TEXT,
                created_at_ms INTEGER NOT NULL,
                cleaned_at_ms INTEGER,
                cleanup_status TEXT
            )
            """
        )
    add_column_if_missing(conn, "operation_approval_artifacts", "request_id TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "artifact_type TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "file_path TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "file_name TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "mime_type TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "size_bytes INTEGER")
    add_column_if_missing(conn, "operation_approval_artifacts", "sha256 TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "meta_json TEXT")
    add_column_if_missing(conn, "operation_approval_artifacts", "created_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_artifacts", "cleaned_at_ms INTEGER")
    add_column_if_missing(conn, "operation_approval_artifacts", "cleanup_status TEXT")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_workflow_steps_operation
        ON operation_approval_workflow_steps(operation_type, step_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_step_approvers_operation
        ON operation_approval_step_approvers(operation_type, step_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_requests_applicant
        ON operation_approval_requests(applicant_user_id, submitted_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_requests_status
        ON operation_approval_requests(status, submitted_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_operation_approval_request_steps_unique
        ON operation_approval_request_steps(request_id, step_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_request_step_approvers_lookup
        ON operation_approval_request_step_approvers(request_id, step_no, approver_user_id, status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_events_request
        ON operation_approval_events(request_id, created_at_ms ASC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_operation_approval_artifacts_request
        ON operation_approval_artifacts(request_id, created_at_ms ASC)
        """
    )


def ensure_user_inbox_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "user_inbox_notifications"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_inbox_notifications (
                inbox_id TEXT PRIMARY KEY,
                recipient_user_id TEXT NOT NULL,
                recipient_username TEXT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                link_path TEXT,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                read_at_ms INTEGER
            )
            """
        )
    add_column_if_missing(conn, "user_inbox_notifications", "recipient_user_id TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "recipient_username TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "title TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "body TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "link_path TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "event_type TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "payload_json TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "status TEXT")
    add_column_if_missing(conn, "user_inbox_notifications", "created_at_ms INTEGER")
    add_column_if_missing(conn, "user_inbox_notifications", "read_at_ms INTEGER")

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_inbox_notifications_recipient
        ON user_inbox_notifications(recipient_user_id, created_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_inbox_notifications_unread
        ON user_inbox_notifications(recipient_user_id, status, created_at_ms DESC)
        """
    )
