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

INTERNAL_AUDIT_STATUSES = {"planned", "in_progress", "completed"}


class InternalAuditService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _serialize(row) -> dict[str, Any]:
        return {
            "audit_id": str(row["audit_id"]),
            "audit_code": str(row["audit_code"]),
            "scope_summary": str(row["scope_summary"]),
            "lead_auditor_user_id": str(row["lead_auditor_user_id"]),
            "planned_at_ms": int(row["planned_at_ms"] or 0),
            "status": str(row["status"]),
            "findings_summary": str(row["findings_summary"]) if row["findings_summary"] else None,
            "conclusion_summary": str(row["conclusion_summary"]) if row["conclusion_summary"] else None,
            "related_capa_id": str(row["related_capa_id"]) if row["related_capa_id"] else None,
            "completed_by_user_id": str(row["completed_by_user_id"]) if row["completed_by_user_id"] else None,
            "completed_at_ms": int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None,
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

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
            raise GovernanceClosureError("related_capa_not_found", status_code=400)
        return normalized

    def get_record(self, audit_id: str) -> dict[str, Any]:
        normalized_id = require_text(audit_id, "audit_id")
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM internal_audit_records WHERE audit_id = ?",
                (normalized_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("internal_audit_not_found", status_code=404)
        return self._serialize(row)

    def list_records(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        normalized_status = optional_text(status)
        if normalized_status is not None:
            normalized_status = require_known_value(
                normalized_status,
                field_name="status",
                allowed=INTERNAL_AUDIT_STATUSES,
            )
        clamped_limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if normalized_status is None:
                rows = conn.execute(
                    """
                    SELECT audit_id
                    FROM internal_audit_records
                    ORDER BY planned_at_ms DESC, audit_id DESC
                    LIMIT ?
                    """,
                    (clamped_limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT audit_id
                    FROM internal_audit_records
                    WHERE status = ?
                    ORDER BY planned_at_ms DESC, audit_id DESC
                    LIMIT ?
                    """,
                    (normalized_status, clamped_limit),
                ).fetchall()
        finally:
            conn.close()
        return [self.get_record(str(row["audit_id"])) for row in rows]

    def create_record(
        self,
        *,
        audit_code: str,
        scope_summary: str,
        lead_auditor_user_id: str,
        planned_at_ms: int,
    ) -> dict[str, Any]:
        normalized_code = require_text(audit_code, "audit_code")
        normalized_scope = require_text(scope_summary, "scope_summary")
        normalized_auditor = require_text(lead_auditor_user_id, "lead_auditor_user_id")
        normalized_planned_at = require_positive_ms(planned_at_ms, "planned_at_ms")
        created_at = now_ms()
        audit_id = new_id("internal_audit")

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicated = conn.execute(
                "SELECT audit_id FROM internal_audit_records WHERE audit_code = ?",
                (normalized_code,),
            ).fetchone()
            if duplicated is not None:
                raise GovernanceClosureError("internal_audit_code_exists", status_code=409)
            conn.execute(
                """
                INSERT INTO internal_audit_records (
                    audit_id,
                    audit_code,
                    scope_summary,
                    lead_auditor_user_id,
                    planned_at_ms,
                    status,
                    findings_summary,
                    conclusion_summary,
                    related_capa_id,
                    completed_by_user_id,
                    completed_at_ms,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, 'planned', NULL, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    audit_id,
                    normalized_code,
                    normalized_scope,
                    normalized_auditor,
                    normalized_planned_at,
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
        return self.get_record(audit_id)

    def complete_record(
        self,
        *,
        audit_id: str,
        findings_summary: str,
        conclusion_summary: str,
        related_capa_id: str | None,
        completed_by_user_id: str,
    ) -> dict[str, Any]:
        normalized_id = require_text(audit_id, "audit_id")
        normalized_findings = require_text(findings_summary, "findings_summary")
        normalized_conclusion = require_text(conclusion_summary, "conclusion_summary")
        normalized_capa = self._ensure_capa_exists(related_capa_id)
        normalized_completed_by = require_text(completed_by_user_id, "completed_by_user_id")
        completed_at = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM internal_audit_records WHERE audit_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("internal_audit_not_found", status_code=404)
            if str(row["status"]) == "completed":
                raise GovernanceClosureError("internal_audit_already_completed", status_code=409)
            conn.execute(
                """
                UPDATE internal_audit_records
                SET status = 'completed',
                    findings_summary = ?,
                    conclusion_summary = ?,
                    related_capa_id = ?,
                    completed_by_user_id = ?,
                    completed_at_ms = ?,
                    updated_at_ms = ?
                WHERE audit_id = ?
                """,
                (
                    normalized_findings,
                    normalized_conclusion,
                    normalized_capa,
                    normalized_completed_by,
                    completed_at,
                    completed_at,
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
        return self.get_record(normalized_id)
