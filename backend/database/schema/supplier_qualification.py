from __future__ import annotations

import sqlite3

from .helpers import add_column_if_missing, table_exists


def ensure_supplier_qualification_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "supplier_component_qualifications"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS supplier_component_qualifications (
                component_code TEXT PRIMARY KEY,
                component_name TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                component_category TEXT NOT NULL,
                deployment_scope TEXT NOT NULL,
                current_version TEXT NOT NULL,
                approved_version TEXT,
                supplier_approval_status TEXT NOT NULL,
                qualification_status TEXT NOT NULL,
                intended_use_summary TEXT NOT NULL,
                qualification_summary TEXT NOT NULL,
                supplier_audit_summary TEXT NOT NULL,
                known_issue_review TEXT NOT NULL,
                revalidation_trigger TEXT,
                migration_plan_summary TEXT NOT NULL,
                review_due_date TEXT,
                approved_by_user_id TEXT,
                approved_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "supplier_component_qualifications", "component_name TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "supplier_name TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "component_category TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "deployment_scope TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "current_version TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "approved_version TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "supplier_approval_status TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "qualification_status TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "intended_use_summary TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "qualification_summary TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "supplier_audit_summary TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "known_issue_review TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "revalidation_trigger TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "migration_plan_summary TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "review_due_date TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "approved_by_user_id TEXT")
    add_column_if_missing(conn, "supplier_component_qualifications", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "supplier_component_qualifications", "created_at_ms INTEGER")
    add_column_if_missing(conn, "supplier_component_qualifications", "updated_at_ms INTEGER")

    if not table_exists(conn, "environment_qualification_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS environment_qualification_records (
                record_id TEXT PRIMARY KEY,
                component_code TEXT NOT NULL,
                environment_name TEXT NOT NULL,
                company_id INTEGER,
                release_version TEXT NOT NULL,
                protocol_ref TEXT NOT NULL,
                iq_status TEXT NOT NULL,
                oq_status TEXT NOT NULL,
                pq_status TEXT NOT NULL,
                qualification_status TEXT NOT NULL,
                qualification_summary TEXT NOT NULL,
                deviation_summary TEXT,
                executed_by_user_id TEXT NOT NULL,
                approved_by_user_id TEXT,
                executed_at_ms INTEGER NOT NULL,
                approved_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "environment_qualification_records", "component_code TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "environment_name TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "company_id INTEGER")
    add_column_if_missing(conn, "environment_qualification_records", "release_version TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "protocol_ref TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "iq_status TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "oq_status TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "pq_status TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "qualification_status TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "qualification_summary TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "deviation_summary TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "executed_by_user_id TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "approved_by_user_id TEXT")
    add_column_if_missing(conn, "environment_qualification_records", "executed_at_ms INTEGER")
    add_column_if_missing(conn, "environment_qualification_records", "approved_at_ms INTEGER")
    add_column_if_missing(conn, "environment_qualification_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "environment_qualification_records", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_component_review_due "
        "ON supplier_component_qualifications(review_due_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_environment_qualification_component_time "
        "ON environment_qualification_records(component_code, executed_at_ms DESC)"
    )
