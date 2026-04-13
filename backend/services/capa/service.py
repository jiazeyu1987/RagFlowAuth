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
    require_text,
    validate_iso_date,
)

CAPA_STATUSES = {"open", "in_progress", "verified", "closed"}


class CapaService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _serialize(row) -> dict[str, Any]:
        return {
            "capa_id": str(row["capa_id"]),
            "capa_code": str(row["capa_code"]),
            "complaint_id": str(row["complaint_id"]) if row["complaint_id"] else None,
            "action_title": str(row["action_title"]),
            "root_cause_summary": str(row["root_cause_summary"]),
            "correction_plan": str(row["correction_plan"]),
            "preventive_plan": str(row["preventive_plan"]),
            "owner_user_id": str(row["owner_user_id"]),
            "due_date": str(row["due_date"]),
            "status": str(row["status"]),
            "effectiveness_summary": str(row["effectiveness_summary"]) if row["effectiveness_summary"] else None,
            "verified_by_user_id": str(row["verified_by_user_id"]) if row["verified_by_user_id"] else None,
            "verified_at_ms": int(row["verified_at_ms"]) if row["verified_at_ms"] is not None else None,
            "closed_by_user_id": str(row["closed_by_user_id"]) if row["closed_by_user_id"] else None,
            "closed_at_ms": int(row["closed_at_ms"]) if row["closed_at_ms"] is not None else None,
            "closure_summary": str(row["closure_summary"]) if row["closure_summary"] else None,
            "created_at_ms": int(row["created_at_ms"] or 0),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
        }

    def _ensure_complaint_exists(self, complaint_id: str | None) -> str | None:
        normalized = optional_text(complaint_id)
        if normalized is None:
            return None
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT complaint_id FROM complaint_cases WHERE complaint_id = ?",
                (normalized,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("complaint_not_found", status_code=400)
        return normalized

    def get_capa(self, capa_id: str) -> dict[str, Any]:
        normalized_id = require_text(capa_id, "capa_id")
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM capa_actions WHERE capa_id = ?", (normalized_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("capa_not_found", status_code=404)
        return self._serialize(row)

    def list_capas(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        normalized_status = optional_text(status)
        if normalized_status is not None:
            normalized_status = require_known_value(
                normalized_status,
                field_name="status",
                allowed=CAPA_STATUSES,
            )
        clamped_limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if normalized_status is None:
                rows = conn.execute(
                    """
                    SELECT capa_id
                    FROM capa_actions
                    ORDER BY created_at_ms DESC, capa_id DESC
                    LIMIT ?
                    """,
                    (clamped_limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT capa_id
                    FROM capa_actions
                    WHERE status = ?
                    ORDER BY created_at_ms DESC, capa_id DESC
                    LIMIT ?
                    """,
                    (normalized_status, clamped_limit),
                ).fetchall()
        finally:
            conn.close()
        return [self.get_capa(str(row["capa_id"])) for row in rows]

    def create_capa(
        self,
        *,
        capa_code: str,
        complaint_id: str | None,
        action_title: str,
        root_cause_summary: str,
        correction_plan: str,
        preventive_plan: str,
        owner_user_id: str,
        due_date: str,
    ) -> dict[str, Any]:
        normalized_code = require_text(capa_code, "capa_code")
        normalized_complaint_id = self._ensure_complaint_exists(complaint_id)
        normalized_title = require_text(action_title, "action_title")
        normalized_root_cause = require_text(root_cause_summary, "root_cause_summary")
        normalized_correction = require_text(correction_plan, "correction_plan")
        normalized_preventive = require_text(preventive_plan, "preventive_plan")
        normalized_owner = require_text(owner_user_id, "owner_user_id")
        normalized_due_date = validate_iso_date(due_date, field_name="due_date")
        created_at = now_ms()
        capa_id = new_id("capa")

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicated = conn.execute(
                "SELECT capa_id FROM capa_actions WHERE capa_code = ?",
                (normalized_code,),
            ).fetchone()
            if duplicated is not None:
                raise GovernanceClosureError("capa_code_exists", status_code=409)
            conn.execute(
                """
                INSERT INTO capa_actions (
                    capa_id,
                    capa_code,
                    complaint_id,
                    action_title,
                    root_cause_summary,
                    correction_plan,
                    preventive_plan,
                    owner_user_id,
                    due_date,
                    status,
                    effectiveness_summary,
                    verified_by_user_id,
                    verified_at_ms,
                    closed_by_user_id,
                    closed_at_ms,
                    closure_summary,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', NULL, NULL, NULL, NULL, NULL, NULL, ?, ?)
                """,
                (
                    capa_id,
                    normalized_code,
                    normalized_complaint_id,
                    normalized_title,
                    normalized_root_cause,
                    normalized_correction,
                    normalized_preventive,
                    normalized_owner,
                    normalized_due_date,
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
        return self.get_capa(capa_id)

    def verify_capa(
        self,
        *,
        capa_id: str,
        effectiveness_summary: str,
        verified_by_user_id: str,
    ) -> dict[str, Any]:
        normalized_id = require_text(capa_id, "capa_id")
        normalized_effectiveness = require_text(effectiveness_summary, "effectiveness_summary")
        normalized_verified_by = require_text(verified_by_user_id, "verified_by_user_id")
        now = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM capa_actions WHERE capa_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("capa_not_found", status_code=404)
            current_status = str(row["status"])
            if current_status == "closed":
                raise GovernanceClosureError("capa_already_closed", status_code=409)
            conn.execute(
                """
                UPDATE capa_actions
                SET status = 'verified',
                    effectiveness_summary = ?,
                    verified_by_user_id = ?,
                    verified_at_ms = ?,
                    updated_at_ms = ?
                WHERE capa_id = ?
                """,
                (
                    normalized_effectiveness,
                    normalized_verified_by,
                    now,
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
        return self.get_capa(normalized_id)

    def close_capa(
        self,
        *,
        capa_id: str,
        closed_by_user_id: str,
        closure_summary: str,
    ) -> dict[str, Any]:
        normalized_id = require_text(capa_id, "capa_id")
        normalized_closed_by = require_text(closed_by_user_id, "closed_by_user_id")
        normalized_summary = require_text(closure_summary, "closure_summary")
        now = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM capa_actions WHERE capa_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("capa_not_found", status_code=404)
            current_status = str(row["status"])
            if current_status == "closed":
                raise GovernanceClosureError("capa_already_closed", status_code=409)
            if current_status != "verified":
                raise GovernanceClosureError("capa_not_verified", status_code=409)
            conn.execute(
                """
                UPDATE capa_actions
                SET status = 'closed',
                    closed_by_user_id = ?,
                    closed_at_ms = ?,
                    closure_summary = ?,
                    updated_at_ms = ?
                WHERE capa_id = ?
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
        return self.get_capa(normalized_id)
