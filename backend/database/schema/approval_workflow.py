from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_approval_workflow_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "approval_workflows"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_workflows (
                workflow_id TEXT PRIMARY KEY,
                kb_ref TEXT NOT NULL,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "approval_workflows", "kb_ref TEXT")
    add_column_if_missing(conn, "approval_workflows", "name TEXT")
    add_column_if_missing(conn, "approval_workflows", "is_active INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "approval_workflows", "created_at_ms INTEGER")
    add_column_if_missing(conn, "approval_workflows", "updated_at_ms INTEGER")

    if not table_exists(conn, "approval_workflow_steps"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_workflow_steps (
                step_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                approver_user_id TEXT,
                approver_role TEXT,
                approver_group_id INTEGER,
                approver_department_id INTEGER,
                approver_company_id INTEGER,
                approval_mode TEXT NOT NULL DEFAULT 'all',
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "approval_workflow_steps", "workflow_id TEXT")
    add_column_if_missing(conn, "approval_workflow_steps", "step_no INTEGER")
    add_column_if_missing(conn, "approval_workflow_steps", "step_name TEXT")
    add_column_if_missing(conn, "approval_workflow_steps", "approver_user_id TEXT")
    add_column_if_missing(conn, "approval_workflow_steps", "approver_role TEXT")
    add_column_if_missing(conn, "approval_workflow_steps", "approver_group_id INTEGER")
    add_column_if_missing(conn, "approval_workflow_steps", "approver_department_id INTEGER")
    add_column_if_missing(conn, "approval_workflow_steps", "approver_company_id INTEGER")
    add_column_if_missing(conn, "approval_workflow_steps", "approval_mode TEXT NOT NULL DEFAULT 'all'")
    add_column_if_missing(conn, "approval_workflow_steps", "created_at_ms INTEGER")

    if not table_exists(conn, "document_approval_instances"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_approval_instances (
                instance_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL UNIQUE,
                workflow_id TEXT NOT NULL,
                current_step_no INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at_ms INTEGER NOT NULL,
                completed_at_ms INTEGER
            )
            """
        )
    add_column_if_missing(conn, "document_approval_instances", "doc_id TEXT")
    add_column_if_missing(conn, "document_approval_instances", "workflow_id TEXT")
    add_column_if_missing(conn, "document_approval_instances", "current_step_no INTEGER")
    add_column_if_missing(conn, "document_approval_instances", "status TEXT")
    add_column_if_missing(conn, "document_approval_instances", "started_at_ms INTEGER")
    add_column_if_missing(conn, "document_approval_instances", "completed_at_ms INTEGER")

    if not table_exists(conn, "document_approval_actions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_approval_actions (
                action_id TEXT PRIMARY KEY,
                instance_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                step_no INTEGER NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                notes TEXT,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "document_approval_actions", "instance_id TEXT")
    add_column_if_missing(conn, "document_approval_actions", "doc_id TEXT")
    add_column_if_missing(conn, "document_approval_actions", "workflow_id TEXT")
    add_column_if_missing(conn, "document_approval_actions", "step_no INTEGER")
    add_column_if_missing(conn, "document_approval_actions", "action TEXT")
    add_column_if_missing(conn, "document_approval_actions", "actor TEXT")
    add_column_if_missing(conn, "document_approval_actions", "notes TEXT")
    add_column_if_missing(conn, "document_approval_actions", "created_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_approval_workflows_kb_ref ON approval_workflows(kb_ref)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_workflow_steps_no ON approval_workflow_steps(workflow_id, step_no)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_approval_instances_doc_id ON document_approval_instances(doc_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_doc_approval_actions_instance_time ON document_approval_actions(instance_id, created_at_ms)"
    )
