from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_change_control_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "change_requests"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS change_requests (
                request_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                requester_user_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                evaluator_user_id TEXT NOT NULL,
                planned_due_date TEXT,
                required_departments_json TEXT NOT NULL,
                affected_controlled_revisions_json TEXT NOT NULL,
                evaluation_summary TEXT,
                plan_summary TEXT,
                execution_summary TEXT,
                close_summary TEXT,
                close_outcome TEXT,
                ledger_writeback_ref TEXT,
                closed_controlled_revisions_json TEXT,
                requested_at_ms INTEGER NOT NULL,
                evaluated_at_ms INTEGER,
                planned_at_ms INTEGER,
                execution_started_at_ms INTEGER,
                execution_completed_at_ms INTEGER,
                confirmed_at_ms INTEGER,
                closed_at_ms INTEGER,
                closed_by_user_id TEXT,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "change_requests", "title TEXT")
    add_column_if_missing(conn, "change_requests", "reason TEXT")
    add_column_if_missing(conn, "change_requests", "status TEXT")
    add_column_if_missing(conn, "change_requests", "requester_user_id TEXT")
    add_column_if_missing(conn, "change_requests", "owner_user_id TEXT")
    add_column_if_missing(conn, "change_requests", "evaluator_user_id TEXT")
    add_column_if_missing(conn, "change_requests", "planned_due_date TEXT")
    add_column_if_missing(conn, "change_requests", "required_departments_json TEXT")
    add_column_if_missing(conn, "change_requests", "affected_controlled_revisions_json TEXT")
    add_column_if_missing(conn, "change_requests", "evaluation_summary TEXT")
    add_column_if_missing(conn, "change_requests", "plan_summary TEXT")
    add_column_if_missing(conn, "change_requests", "execution_summary TEXT")
    add_column_if_missing(conn, "change_requests", "close_summary TEXT")
    add_column_if_missing(conn, "change_requests", "close_outcome TEXT")
    add_column_if_missing(conn, "change_requests", "ledger_writeback_ref TEXT")
    add_column_if_missing(conn, "change_requests", "closed_controlled_revisions_json TEXT")
    add_column_if_missing(conn, "change_requests", "requested_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "evaluated_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "planned_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "execution_started_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "execution_completed_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "confirmed_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "closed_at_ms INTEGER")
    add_column_if_missing(conn, "change_requests", "closed_by_user_id TEXT")
    add_column_if_missing(conn, "change_requests", "updated_at_ms INTEGER")

    if not table_exists(conn, "change_plan_items"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS change_plan_items (
                plan_item_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                title TEXT NOT NULL,
                assignee_user_id TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                completion_note TEXT,
                completed_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "change_plan_items", "request_id TEXT")
    add_column_if_missing(conn, "change_plan_items", "title TEXT")
    add_column_if_missing(conn, "change_plan_items", "assignee_user_id TEXT")
    add_column_if_missing(conn, "change_plan_items", "due_date TEXT")
    add_column_if_missing(conn, "change_plan_items", "status TEXT")
    add_column_if_missing(conn, "change_plan_items", "completion_note TEXT")
    add_column_if_missing(conn, "change_plan_items", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "change_plan_items", "created_at_ms INTEGER")
    add_column_if_missing(conn, "change_plan_items", "updated_at_ms INTEGER")

    if not table_exists(conn, "change_confirmations"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS change_confirmations (
                confirmation_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                department_code TEXT NOT NULL,
                confirmed_by_user_id TEXT NOT NULL,
                notes TEXT,
                confirmed_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "change_confirmations", "request_id TEXT")
    add_column_if_missing(conn, "change_confirmations", "department_code TEXT")
    add_column_if_missing(conn, "change_confirmations", "confirmed_by_user_id TEXT")
    add_column_if_missing(conn, "change_confirmations", "notes TEXT")
    add_column_if_missing(conn, "change_confirmations", "confirmed_at_ms INTEGER")

    if not table_exists(conn, "change_request_actions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS change_request_actions (
                action_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "change_request_actions", "request_id TEXT")
    add_column_if_missing(conn, "change_request_actions", "action TEXT")
    add_column_if_missing(conn, "change_request_actions", "actor_user_id TEXT")
    add_column_if_missing(conn, "change_request_actions", "details_json TEXT")
    add_column_if_missing(conn, "change_request_actions", "created_at_ms INTEGER")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_change_requests_status ON change_requests(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_change_requests_updated ON change_requests(updated_at_ms DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_change_plan_items_request ON change_plan_items(request_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_change_plan_items_due_status ON change_plan_items(due_date, status)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_change_confirmations_request_dept "
        "ON change_confirmations(request_id, department_code)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_change_request_actions_request_time "
        "ON change_request_actions(request_id, created_at_ms)"
    )
