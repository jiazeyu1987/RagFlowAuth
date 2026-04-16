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
                file_subtype TEXT,
                product_name TEXT,
                registration_ref TEXT,
                target_kb_id TEXT NOT NULL,
                target_kb_name TEXT,
                distribution_department_ids_json TEXT,
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
    add_column_if_missing(conn, "controlled_documents", "file_subtype TEXT")
    add_column_if_missing(conn, "controlled_documents", "product_name TEXT")
    add_column_if_missing(conn, "controlled_documents", "registration_ref TEXT")
    add_column_if_missing(conn, "controlled_documents", "target_kb_id TEXT")
    add_column_if_missing(conn, "controlled_documents", "target_kb_name TEXT")
    add_column_if_missing(conn, "controlled_documents", "distribution_department_ids_json TEXT")
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
                file_subtype TEXT,
                status TEXT NOT NULL,
                change_summary TEXT,
                previous_revision_id TEXT,
                approval_request_id TEXT,
                approval_last_request_id TEXT,
                approval_round INTEGER NOT NULL DEFAULT 0,
                approval_submitted_at_ms INTEGER,
                approval_completed_at_ms INTEGER,
                current_approval_step_no INTEGER,
                current_approval_step_name TEXT,
                current_approval_step_timeout_reminder_minutes INTEGER,
                current_approval_step_overdue_at_ms INTEGER,
                current_approval_step_last_reminded_at_ms INTEGER,
                release_mode TEXT,
                release_manual_archive_completed_by TEXT,
                release_manual_archive_completed_at_ms INTEGER,
                approved_by TEXT,
                approved_at_ms INTEGER,
                matrix_snapshot_json TEXT,
                position_snapshot_json TEXT,
                effective_at_ms INTEGER,
                obsolete_at_ms INTEGER,
                superseded_at_ms INTEGER,
                superseded_by_revision_id TEXT,
                created_by TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "controlled_revisions", "controlled_document_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "kb_doc_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "revision_no INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "file_subtype TEXT")
    add_column_if_missing(conn, "controlled_revisions", "status TEXT")
    add_column_if_missing(conn, "controlled_revisions", "change_summary TEXT")
    add_column_if_missing(conn, "controlled_revisions", "previous_revision_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approval_request_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approval_last_request_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approval_round INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "controlled_revisions", "approval_submitted_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "approval_completed_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "current_approval_step_no INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "current_approval_step_name TEXT")
    add_column_if_missing(conn, "controlled_revisions", "current_approval_step_timeout_reminder_minutes INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "current_approval_step_overdue_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "current_approval_step_last_reminded_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "release_mode TEXT")
    add_column_if_missing(conn, "controlled_revisions", "release_manual_archive_completed_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "release_manual_archive_completed_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "approved_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "matrix_snapshot_json TEXT")
    add_column_if_missing(conn, "controlled_revisions", "position_snapshot_json TEXT")
    add_column_if_missing(conn, "controlled_revisions", "effective_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "superseded_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "superseded_by_revision_id TEXT")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_requested_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_requested_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_reason TEXT")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_retention_until_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_approved_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "obsolete_approved_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "destruction_confirmed_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "destruction_confirmed_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "destruction_notes TEXT")
    add_column_if_missing(conn, "controlled_revisions", "created_by TEXT")
    add_column_if_missing(conn, "controlled_revisions", "created_at_ms INTEGER")
    add_column_if_missing(conn, "controlled_revisions", "updated_at_ms INTEGER")

    if not table_exists(conn, "controlled_revision_release_ledger"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS controlled_revision_release_ledger (
                ledger_id TEXT PRIMARY KEY,
                controlled_document_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                release_mode TEXT NOT NULL,
                subject_revision_id TEXT NOT NULL,
                other_revision_id TEXT,
                actor_user_id TEXT NOT NULL,
                actor_username TEXT,
                created_at_ms INTEGER NOT NULL,
                note TEXT
            )
            """
        )

    if not table_exists(conn, "document_control_approval_workflows"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_control_approval_workflows (
                document_type TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "document_control_approval_workflows", "document_type TEXT")
    add_column_if_missing(conn, "document_control_approval_workflows", "name TEXT")
    add_column_if_missing(conn, "document_control_approval_workflows", "is_active INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "document_control_approval_workflows", "created_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_approval_workflows", "updated_at_ms INTEGER")

    if not table_exists(conn, "document_control_approval_workflow_steps"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_control_approval_workflow_steps (
                workflow_step_id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                step_type TEXT NOT NULL,
                approval_rule TEXT NOT NULL,
                member_source TEXT NOT NULL,
                timeout_reminder_minutes INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "document_type TEXT")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "step_no INTEGER")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "step_type TEXT")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "approval_rule TEXT NOT NULL")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "member_source TEXT NOT NULL")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "timeout_reminder_minutes INTEGER NOT NULL")
    add_column_if_missing(conn, "document_control_approval_workflow_steps", "created_at_ms INTEGER")

    if not table_exists(conn, "document_control_approval_step_approvers"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_control_approval_step_approvers (
                workflow_step_approver_id TEXT PRIMARY KEY,
                workflow_step_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                approver_user_id TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "document_control_approval_step_approvers", "workflow_step_id TEXT")
    add_column_if_missing(conn, "document_control_approval_step_approvers", "document_type TEXT")
    add_column_if_missing(conn, "document_control_approval_step_approvers", "step_no INTEGER")
    add_column_if_missing(conn, "document_control_approval_step_approvers", "approver_user_id TEXT")
    add_column_if_missing(conn, "document_control_approval_step_approvers", "created_at_ms INTEGER")

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
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_revisions_approval_request
        ON controlled_revisions(approval_request_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_revisions_approval_overdue
        ON controlled_revisions(status, current_approval_step_overdue_at_ms, current_approval_step_last_reminded_at_ms)
        """
    )

    if not table_exists(conn, "document_control_department_acks"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_control_department_acks (
                ack_id TEXT PRIMARY KEY,
                controlled_revision_id TEXT NOT NULL,
                controlled_document_id TEXT NOT NULL,
                department_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                due_at_ms INTEGER NOT NULL,
                confirmed_by_user_id TEXT,
                confirmed_at_ms INTEGER,
                overdue_at_ms INTEGER,
                last_reminded_at_ms INTEGER,
                notes TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )

    add_column_if_missing(conn, "document_control_department_acks", "controlled_revision_id TEXT")
    add_column_if_missing(conn, "document_control_department_acks", "controlled_document_id TEXT")
    add_column_if_missing(conn, "document_control_department_acks", "department_id INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "status TEXT")
    add_column_if_missing(conn, "document_control_department_acks", "due_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "confirmed_by_user_id TEXT")
    add_column_if_missing(conn, "document_control_department_acks", "confirmed_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "overdue_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "last_reminded_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "notes TEXT")
    add_column_if_missing(conn, "document_control_department_acks", "created_at_ms INTEGER")
    add_column_if_missing(conn, "document_control_department_acks", "updated_at_ms INTEGER")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_ctrl_dept_acks_unique
        ON document_control_department_acks(controlled_revision_id, department_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_doc_ctrl_dept_acks_doc_rev
        ON document_control_department_acks(controlled_document_id, controlled_revision_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_doc_ctrl_dept_acks_due
        ON document_control_department_acks(status, due_at_ms)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_revision_release_ledger_doc_time
        ON controlled_revision_release_ledger(controlled_document_id, created_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_controlled_revision_release_ledger_subject
        ON controlled_revision_release_ledger(subject_revision_id, created_at_ms DESC)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_ctrl_workflow_step_unique
        ON document_control_approval_workflow_steps(document_type, step_no)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_doc_ctrl_workflow_step_doc_type
        ON document_control_approval_workflow_steps(document_type, step_no)
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_doc_ctrl_workflow_step_approver_unique
        ON document_control_approval_step_approvers(document_type, step_no, approver_user_id)
        """
    )
