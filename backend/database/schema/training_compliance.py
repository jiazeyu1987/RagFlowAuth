from __future__ import annotations

import sqlite3
import time

from .helpers import add_column_if_missing, table_exists


def ensure_training_compliance_tables(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "training_requirements"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS training_requirements (
                requirement_code TEXT PRIMARY KEY,
                requirement_name TEXT NOT NULL,
                role_code TEXT NOT NULL,
                controlled_action TEXT NOT NULL,
                curriculum_version TEXT NOT NULL,
                training_material_ref TEXT NOT NULL,
                effectiveness_required INTEGER NOT NULL DEFAULT 1,
                recertification_interval_days INTEGER NOT NULL,
                review_due_date TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "training_requirements", "requirement_name TEXT")
    add_column_if_missing(conn, "training_requirements", "role_code TEXT")
    add_column_if_missing(conn, "training_requirements", "controlled_action TEXT")
    add_column_if_missing(conn, "training_requirements", "curriculum_version TEXT")
    add_column_if_missing(conn, "training_requirements", "training_material_ref TEXT")
    add_column_if_missing(conn, "training_requirements", "effectiveness_required INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "training_requirements", "recertification_interval_days INTEGER NOT NULL DEFAULT 365")
    add_column_if_missing(conn, "training_requirements", "review_due_date TEXT")
    add_column_if_missing(conn, "training_requirements", "active INTEGER NOT NULL DEFAULT 1")
    add_column_if_missing(conn, "training_requirements", "created_at_ms INTEGER")
    add_column_if_missing(conn, "training_requirements", "updated_at_ms INTEGER")

    if not table_exists(conn, "training_records"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS training_records (
                record_id TEXT PRIMARY KEY,
                requirement_code TEXT NOT NULL,
                user_id TEXT NOT NULL,
                curriculum_version TEXT NOT NULL,
                trainer_user_id TEXT NOT NULL,
                training_outcome TEXT NOT NULL,
                effectiveness_status TEXT NOT NULL,
                effectiveness_score REAL,
                effectiveness_summary TEXT NOT NULL,
                training_notes TEXT,
                completed_at_ms INTEGER NOT NULL,
                effectiveness_reviewed_by_user_id TEXT,
                effectiveness_reviewed_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "training_records", "requirement_code TEXT")
    add_column_if_missing(conn, "training_records", "user_id TEXT")
    add_column_if_missing(conn, "training_records", "curriculum_version TEXT")
    add_column_if_missing(conn, "training_records", "trainer_user_id TEXT")
    add_column_if_missing(conn, "training_records", "training_outcome TEXT")
    add_column_if_missing(conn, "training_records", "effectiveness_status TEXT")
    add_column_if_missing(conn, "training_records", "effectiveness_score REAL")
    add_column_if_missing(conn, "training_records", "effectiveness_summary TEXT")
    add_column_if_missing(conn, "training_records", "training_notes TEXT")
    add_column_if_missing(conn, "training_records", "completed_at_ms INTEGER")
    add_column_if_missing(conn, "training_records", "effectiveness_reviewed_by_user_id TEXT")
    add_column_if_missing(conn, "training_records", "effectiveness_reviewed_at_ms INTEGER")
    add_column_if_missing(conn, "training_records", "created_at_ms INTEGER")
    add_column_if_missing(conn, "training_records", "updated_at_ms INTEGER")

    if not table_exists(conn, "operator_certifications"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_certifications (
                certification_id TEXT PRIMARY KEY,
                requirement_code TEXT NOT NULL,
                user_id TEXT NOT NULL,
                curriculum_version TEXT NOT NULL,
                certification_status TEXT NOT NULL,
                granted_by_user_id TEXT NOT NULL,
                valid_until_ms INTEGER NOT NULL,
                exception_release_ref TEXT,
                certification_notes TEXT,
                granted_at_ms INTEGER NOT NULL,
                revoked_at_ms INTEGER,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            )
            """
        )
    add_column_if_missing(conn, "operator_certifications", "requirement_code TEXT")
    add_column_if_missing(conn, "operator_certifications", "user_id TEXT")
    add_column_if_missing(conn, "operator_certifications", "curriculum_version TEXT")
    add_column_if_missing(conn, "operator_certifications", "certification_status TEXT")
    add_column_if_missing(conn, "operator_certifications", "granted_by_user_id TEXT")
    add_column_if_missing(conn, "operator_certifications", "valid_until_ms INTEGER")
    add_column_if_missing(conn, "operator_certifications", "exception_release_ref TEXT")
    add_column_if_missing(conn, "operator_certifications", "certification_notes TEXT")
    add_column_if_missing(conn, "operator_certifications", "granted_at_ms INTEGER")
    add_column_if_missing(conn, "operator_certifications", "revoked_at_ms INTEGER")
    add_column_if_missing(conn, "operator_certifications", "created_at_ms INTEGER")
    add_column_if_missing(conn, "operator_certifications", "updated_at_ms INTEGER")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_requirements_action_role "
        "ON training_requirements(controlled_action, role_code, active)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_training_records_requirement_user_time "
        "ON training_records(requirement_code, user_id, completed_at_ms DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_operator_certifications_requirement_user_time "
        "ON operator_certifications(requirement_code, user_id, granted_at_ms DESC)"
    )

    seed_default_training_requirements(conn)


def seed_default_training_requirements(conn: sqlite3.Connection) -> None:
    now_ms = int(time.time() * 1000)
    defaults = (
        (
            "TR-001",
            "审批与发布操作员培训",
            "reviewer",
            "document_review",
            "2026.04",
            "doc/compliance/training_matrix.md#tr-001",
            1,
            365,
            "2026-10-03",
            1,
        ),
        (
            "TR-002",
            "恢复演练操作员培训",
            "admin",
            "restore_drill_execute",
            "2026.04",
            "doc/compliance/training_matrix.md#tr-002",
            1,
            365,
            "2026-10-03",
            1,
        ),
    )
    for item in defaults:
        existing = conn.execute(
            "SELECT requirement_code FROM training_requirements WHERE requirement_code = ?",
            (item[0],),
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO training_requirements (
                requirement_code,
                requirement_name,
                role_code,
                controlled_action,
                curriculum_version,
                training_material_ref,
                effectiveness_required,
                recertification_interval_days,
                review_due_date,
                active,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            item + (now_ms, now_ms),
        )
