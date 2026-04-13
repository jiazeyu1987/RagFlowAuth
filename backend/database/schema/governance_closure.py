from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_governance_closure_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "complaint_cases"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS complaint_cases (
                complaint_id TEXT PRIMARY KEY,
                complaint_code TEXT NOT NULL UNIQUE,
                source_channel TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                reported_by_user_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                related_supplier_component_code TEXT,
                related_environment_record_id TEXT,
                received_at_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                disposition_summary TEXT,
                linked_capa_id TEXT,
                closed_by_user_id TEXT,
                closed_at_ms INTEGER,
                closure_summary TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "complaint_cases", "complaint_code TEXT")
    add_column_if_missing(conn, "complaint_cases", "source_channel TEXT")
    add_column_if_missing(conn, "complaint_cases", "severity_level TEXT")
    add_column_if_missing(conn, "complaint_cases", "subject TEXT")
    add_column_if_missing(conn, "complaint_cases", "description TEXT")
    add_column_if_missing(conn, "complaint_cases", "reported_by_user_id TEXT")
    add_column_if_missing(conn, "complaint_cases", "owner_user_id TEXT")
    add_column_if_missing(conn, "complaint_cases", "related_supplier_component_code TEXT")
    add_column_if_missing(conn, "complaint_cases", "related_environment_record_id TEXT")
    add_column_if_missing(conn, "complaint_cases", "received_at_ms INTEGER")
    add_column_if_missing(conn, "complaint_cases", "status TEXT")
    add_column_if_missing(conn, "complaint_cases", "disposition_summary TEXT")
    add_column_if_missing(conn, "complaint_cases", "linked_capa_id TEXT")
    add_column_if_missing(conn, "complaint_cases", "closed_by_user_id TEXT")
    add_column_if_missing(conn, "complaint_cases", "closed_at_ms INTEGER")
    add_column_if_missing(conn, "complaint_cases", "closure_summary TEXT")
    add_column_if_missing(conn, "complaint_cases", "created_at_ms INTEGER")
    add_column_if_missing(conn, "complaint_cases", "updated_at_ms INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_complaint_cases_status_time "
        "ON complaint_cases(status, received_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_complaint_cases_code ON complaint_cases(complaint_code)"
    )

    if not table_exists(conn, "capa_actions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capa_actions (
                capa_id TEXT PRIMARY KEY,
                capa_code TEXT NOT NULL UNIQUE,
                complaint_id TEXT,
                action_title TEXT NOT NULL,
                root_cause_summary TEXT NOT NULL,
                correction_plan TEXT NOT NULL,
                preventive_plan TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                effectiveness_summary TEXT,
                verified_by_user_id TEXT,
                verified_at_ms INTEGER,
                closed_by_user_id TEXT,
                closed_at_ms INTEGER,
                closure_summary TEXT,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "capa_actions", "capa_code TEXT")
    add_column_if_missing(conn, "capa_actions", "complaint_id TEXT")
    add_column_if_missing(conn, "capa_actions", "action_title TEXT")
    add_column_if_missing(conn, "capa_actions", "root_cause_summary TEXT")
    add_column_if_missing(conn, "capa_actions", "correction_plan TEXT")
    add_column_if_missing(conn, "capa_actions", "preventive_plan TEXT")
    add_column_if_missing(conn, "capa_actions", "owner_user_id TEXT")
    add_column_if_missing(conn, "capa_actions", "due_date TEXT")
    add_column_if_missing(conn, "capa_actions", "status TEXT")
    add_column_if_missing(conn, "capa_actions", "effectiveness_summary TEXT")
    add_column_if_missing(conn, "capa_actions", "verified_by_user_id TEXT")
    add_column_if_missing(conn, "capa_actions", "verified_at_ms INTEGER")
    add_column_if_missing(conn, "capa_actions", "closed_by_user_id TEXT")
    add_column_if_missing(conn, "capa_actions", "closed_at_ms INTEGER")
    add_column_if_missing(conn, "capa_actions", "closure_summary TEXT")
    add_column_if_missing(conn, "capa_actions", "created_at_ms INTEGER")
    add_column_if_missing(conn, "capa_actions", "updated_at_ms INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_capa_actions_status_due "
        "ON capa_actions(status, due_date ASC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_capa_actions_complaint ON capa_actions(complaint_id)"
    )

    if not table_exists(conn, "internal_audit_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS internal_audit_records (
                audit_id TEXT PRIMARY KEY,
                audit_code TEXT NOT NULL UNIQUE,
                scope_summary TEXT NOT NULL,
                lead_auditor_user_id TEXT NOT NULL,
                planned_at_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                findings_summary TEXT,
                conclusion_summary TEXT,
                related_capa_id TEXT,
                completed_by_user_id TEXT,
                completed_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "internal_audit_records", "audit_code TEXT")
    add_column_if_missing(conn, "internal_audit_records", "scope_summary TEXT")
    add_column_if_missing(conn, "internal_audit_records", "lead_auditor_user_id TEXT")
    add_column_if_missing(conn, "internal_audit_records", "planned_at_ms INTEGER")
    add_column_if_missing(conn, "internal_audit_records", "status TEXT")
    add_column_if_missing(conn, "internal_audit_records", "findings_summary TEXT")
    add_column_if_missing(conn, "internal_audit_records", "conclusion_summary TEXT")
    add_column_if_missing(conn, "internal_audit_records", "related_capa_id TEXT")
    add_column_if_missing(conn, "internal_audit_records", "completed_by_user_id TEXT")
    add_column_if_missing(conn, "internal_audit_records", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "internal_audit_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "internal_audit_records", "updated_at_ms INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_internal_audits_status_planned "
        "ON internal_audit_records(status, planned_at_ms DESC)"
    )

    if not table_exists(conn, "management_review_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS management_review_records (
                review_id TEXT PRIMARY KEY,
                review_code TEXT NOT NULL UNIQUE,
                meeting_at_ms INTEGER NOT NULL,
                chair_user_id TEXT NOT NULL,
                input_summary TEXT NOT NULL,
                output_summary TEXT,
                decision_summary TEXT,
                follow_up_capa_id TEXT,
                status TEXT NOT NULL,
                completed_by_user_id TEXT,
                completed_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "management_review_records", "review_code TEXT")
    add_column_if_missing(conn, "management_review_records", "meeting_at_ms INTEGER")
    add_column_if_missing(conn, "management_review_records", "chair_user_id TEXT")
    add_column_if_missing(conn, "management_review_records", "input_summary TEXT")
    add_column_if_missing(conn, "management_review_records", "output_summary TEXT")
    add_column_if_missing(conn, "management_review_records", "decision_summary TEXT")
    add_column_if_missing(conn, "management_review_records", "follow_up_capa_id TEXT")
    add_column_if_missing(conn, "management_review_records", "status TEXT")
    add_column_if_missing(conn, "management_review_records", "completed_by_user_id TEXT")
    add_column_if_missing(conn, "management_review_records", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "management_review_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "management_review_records", "updated_at_ms INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_management_reviews_status_meeting "
        "ON management_review_records(status, meeting_at_ms DESC)"
    )
