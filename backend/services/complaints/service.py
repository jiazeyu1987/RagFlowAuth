from __future__ import annotations

from typing import Any

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite
from backend.services.governance_shared import (
    GovernanceClosureError,
    new_id,
    now_ms,
    optional_text,
    require_known_value,
    require_positive_ms,
    require_text,
)

COMPLAINT_SOURCES = {"customer", "internal", "regulatory", "supplier"}
COMPLAINT_SEVERITIES = {"minor", "major", "critical"}
COMPLAINT_STATUSES = {"open", "investigating", "capa_required", "closed"}


class ComplaintService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _serialize(row) -> dict[str, Any]:
        return {
            "complaint_id": str(row["complaint_id"]),
            "complaint_code": str(row["complaint_code"]),
            "source_channel": str(row["source_channel"]),
            "severity_level": str(row["severity_level"]),
            "subject": str(row["subject"]),
            "description": str(row["description"]),
            "reported_by_user_id": str(row["reported_by_user_id"]),
            "owner_user_id": str(row["owner_user_id"]),
            "related_supplier_component_code": (
                str(row["related_supplier_component_code"]) if row["related_supplier_component_code"] else None
            ),
            "related_environment_record_id": (
                str(row["related_environment_record_id"]) if row["related_environment_record_id"] else None
            ),
            "received_at_ms": int(row["received_at_ms"] or 0),
            "status": str(row["status"]),
            "disposition_summary": str(row["disposition_summary"]) if row["disposition_summary"] else None,
            "linked_capa_id": str(row["linked_capa_id"]) if row["linked_capa_id"] else None,
            "closed_by_user_id": str(row["closed_by_user_id"]) if row["closed_by_user_id"] else None,
            "closed_at_ms": int(row["closed_at_ms"]) if row["closed_at_ms"] is not None else None,
            "closure_summary": str(row["closure_summary"]) if row["closure_summary"] else None,
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    def _ensure_component_exists(self, component_code: str | None) -> str | None:
        normalized = optional_text(component_code)
        if normalized is None:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT component_code FROM supplier_component_qualifications WHERE component_code = ?",
                (normalized,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("related_supplier_component_not_found", status_code=400)
        return normalized

    def _ensure_environment_record_exists(self, record_id: str | None) -> str | None:
        normalized = optional_text(record_id)
        if normalized is None:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT record_id FROM environment_qualification_records WHERE record_id = ?",
                (normalized,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("related_environment_record_not_found", status_code=400)
        return normalized

    def _ensure_capa_exists(self, capa_id: str | None) -> str | None:
        normalized = optional_text(capa_id)
        if normalized is None:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT capa_id FROM capa_actions WHERE capa_id = ?",
                (normalized,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("linked_capa_not_found", status_code=400)
        return normalized

    def get_complaint(self, complaint_id: str) -> dict[str, Any]:
        normalized_id = require_text(complaint_id, "complaint_id")
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM complaint_cases WHERE complaint_id = ?",
                (normalized_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("complaint_not_found", status_code=404)
        return self._serialize(row)

    def list_complaints(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        normalized_status = optional_text(status)
        if normalized_status is not None:
            normalized_status = require_known_value(
                normalized_status,
                field_name="status",
                allowed=COMPLAINT_STATUSES,
            )
        clamped_limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if normalized_status is None:
                rows = conn.execute(
                    """
                    SELECT complaint_id
                    FROM complaint_cases
                    ORDER BY received_at_ms DESC, complaint_id DESC
                    LIMIT ?
                    """,
                    (clamped_limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT complaint_id
                    FROM complaint_cases
                    WHERE status = ?
                    ORDER BY received_at_ms DESC, complaint_id DESC
                    LIMIT ?
                    """,
                    (normalized_status, clamped_limit),
                ).fetchall()
        finally:
            conn.close()
        return [self.get_complaint(str(row["complaint_id"])) for row in rows]

    def create_complaint(
        self,
        *,
        complaint_code: str,
        source_channel: str,
        severity_level: str,
        subject: str,
        description: str,
        reported_by_user_id: str,
        owner_user_id: str,
        related_supplier_component_code: str | None = None,
        related_environment_record_id: str | None = None,
        received_at_ms: int | None = None,
    ) -> dict[str, Any]:
        normalized_code = require_text(complaint_code, "complaint_code")
        normalized_source = require_known_value(
            source_channel,
            field_name="source_channel",
            allowed=COMPLAINT_SOURCES,
        )
        normalized_severity = require_known_value(
            severity_level,
            field_name="severity_level",
            allowed=COMPLAINT_SEVERITIES,
        )
        normalized_subject = require_text(subject, "subject")
        normalized_description = require_text(description, "description")
        normalized_reported_by = require_text(reported_by_user_id, "reported_by_user_id")
        normalized_owner = require_text(owner_user_id, "owner_user_id")
        component_ref = self._ensure_component_exists(related_supplier_component_code)
        env_ref = self._ensure_environment_record_exists(related_environment_record_id)
        when_ms = now_ms() if received_at_ms is None else require_positive_ms(received_at_ms, "received_at_ms")
        created_at = now_ms()
        complaint_id = new_id("complaint")

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicated = conn.execute(
                "SELECT complaint_id FROM complaint_cases WHERE complaint_code = ?",
                (normalized_code,),
            ).fetchone()
            if duplicated is not None:
                raise GovernanceClosureError("complaint_code_exists", status_code=409)
            conn.execute(
                """
                INSERT INTO complaint_cases (
                    complaint_id,
                    complaint_code,
                    source_channel,
                    severity_level,
                    subject,
                    description,
                    reported_by_user_id,
                    owner_user_id,
                    related_supplier_component_code,
                    related_environment_record_id,
                    received_at_ms,
                    status,
                    disposition_summary,
                    linked_capa_id,
                    closed_by_user_id,
                    closed_at_ms,
                    closure_summary,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', NULL, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    complaint_id,
                    normalized_code,
                    normalized_source,
                    normalized_severity,
                    normalized_subject,
                    normalized_description,
                    normalized_reported_by,
                    normalized_owner,
                    component_ref,
                    env_ref,
                    when_ms,
                    created_at,
                    created_at,
                ),
            )
            conn.commit()
        except GovernanceClosureError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_complaint(complaint_id)

    def assess_complaint(
        self,
        *,
        complaint_id: str,
        status: str,
        disposition_summary: str,
        linked_capa_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_id = require_text(complaint_id, "complaint_id")
        normalized_status = require_known_value(status, field_name="status", allowed={"investigating", "capa_required"})
        normalized_disposition = require_text(disposition_summary, "disposition_summary")
        normalized_capa = self._ensure_capa_exists(linked_capa_id)
        now = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM complaint_cases WHERE complaint_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("complaint_not_found", status_code=404)
            if str(row["status"]) == "closed":
                raise GovernanceClosureError("complaint_already_closed", status_code=409)
            conn.execute(
                """
                UPDATE complaint_cases
                SET status = ?,
                    disposition_summary = ?,
                    linked_capa_id = ?,
                    updated_at_ms = ?
                WHERE complaint_id = ?
                """,
                (
                    normalized_status,
                    normalized_disposition,
                    normalized_capa,
                    now,
                    normalized_id,
                ),
            )
            conn.commit()
        except GovernanceClosureError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_complaint(normalized_id)

    def close_complaint(
        self,
        *,
        complaint_id: str,
        closed_by_user_id: str,
        closure_summary: str,
    ) -> dict[str, Any]:
        normalized_id = require_text(complaint_id, "complaint_id")
        normalized_closed_by = require_text(closed_by_user_id, "closed_by_user_id")
        normalized_summary = require_text(closure_summary, "closure_summary")
        now = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM complaint_cases WHERE complaint_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("complaint_not_found", status_code=404)
            if str(row["status"]) == "closed":
                raise GovernanceClosureError("complaint_already_closed", status_code=409)
            conn.execute(
                """
                UPDATE complaint_cases
                SET status = 'closed',
                    closed_by_user_id = ?,
                    closed_at_ms = ?,
                    closure_summary = ?,
                    updated_at_ms = ?
                WHERE complaint_id = ?
                """,
                (
                    normalized_closed_by,
                    now,
                    normalized_summary,
                    now,
                    normalized_id,
                ),
            )
            conn.commit()
        except GovernanceClosureError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_complaint(normalized_id)
