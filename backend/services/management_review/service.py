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

MANAGEMENT_REVIEW_STATUSES = {"planned", "completed"}


class ManagementReviewService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _serialize(row) -> dict[str, Any]:
        return {
            "review_id": str(row["review_id"]),
            "review_code": str(row["review_code"]),
            "meeting_at_ms": int(row["meeting_at_ms"] or 0),
            "chair_user_id": str(row["chair_user_id"]),
            "input_summary": str(row["input_summary"]),
            "output_summary": str(row["output_summary"]) if row["output_summary"] else None,
            "decision_summary": str(row["decision_summary"]) if row["decision_summary"] else None,
            "follow_up_capa_id": str(row["follow_up_capa_id"]) if row["follow_up_capa_id"] else None,
            "status": str(row["status"]),
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
            raise GovernanceClosureError("follow_up_capa_not_found", status_code=400)
        return normalized

    def get_record(self, review_id: str) -> dict[str, Any]:
        normalized_id = require_text(review_id, "review_id")
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM management_review_records WHERE review_id = ?",
                (normalized_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise GovernanceClosureError("management_review_not_found", status_code=404)
        return self._serialize(row)

    def list_records(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        normalized_status = optional_text(status)
        if normalized_status is not None:
            normalized_status = require_known_value(
                normalized_status,
                field_name="status",
                allowed=MANAGEMENT_REVIEW_STATUSES,
            )
        clamped_limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if normalized_status is None:
                rows = conn.execute(
                    """
                    SELECT review_id
                    FROM management_review_records
                    ORDER BY meeting_at_ms DESC, review_id DESC
                    LIMIT ?
                    """,
                    (clamped_limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT review_id
                    FROM management_review_records
                    WHERE status = ?
                    ORDER BY meeting_at_ms DESC, review_id DESC
                    LIMIT ?
                    """,
                    (normalized_status, clamped_limit),
                ).fetchall()
        finally:
            conn.close()
        return [self.get_record(str(row["review_id"])) for row in rows]

    def create_record(
        self,
        *,
        review_code: str,
        meeting_at_ms: int,
        chair_user_id: str,
        input_summary: str,
    ) -> dict[str, Any]:
        normalized_code = require_text(review_code, "review_code")
        normalized_meeting_at = require_positive_ms(meeting_at_ms, "meeting_at_ms")
        normalized_chair = require_text(chair_user_id, "chair_user_id")
        normalized_input = require_text(input_summary, "input_summary")
        created_at = now_ms()
        review_id = new_id("management_review")

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            duplicated = conn.execute(
                "SELECT review_id FROM management_review_records WHERE review_code = ?",
                (normalized_code,),
            ).fetchone()
            if duplicated is not None:
                raise GovernanceClosureError("management_review_code_exists", status_code=409)
            conn.execute(
                """
                INSERT INTO management_review_records (
                    review_id,
                    review_code,
                    meeting_at_ms,
                    chair_user_id,
                    input_summary,
                    output_summary,
                    decision_summary,
                    follow_up_capa_id,
                    status,
                    completed_by_user_id,
                    completed_at_ms,
                    created_at_ms,
                    updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, 'planned', NULL, NULL, ?, ?)
                """,
                (
                    review_id,
                    normalized_code,
                    normalized_meeting_at,
                    normalized_chair,
                    normalized_input,
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
        return self.get_record(review_id)

    def complete_record(
        self,
        *,
        review_id: str,
        output_summary: str,
        decision_summary: str,
        follow_up_capa_id: str | None,
        completed_by_user_id: str,
    ) -> dict[str, Any]:
        normalized_id = require_text(review_id, "review_id")
        normalized_output = require_text(output_summary, "output_summary")
        normalized_decision = require_text(decision_summary, "decision_summary")
        normalized_follow_up_capa = self._ensure_capa_exists(follow_up_capa_id)
        normalized_completed_by = require_text(completed_by_user_id, "completed_by_user_id")
        completed_at = now_ms()

        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status FROM management_review_records WHERE review_id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise GovernanceClosureError("management_review_not_found", status_code=404)
            if str(row["status"]) == "completed":
                raise GovernanceClosureError("management_review_already_completed", status_code=409)
            conn.execute(
                """
                UPDATE management_review_records
                SET status = 'completed',
                    output_summary = ?,
                    decision_summary = ?,
                    follow_up_capa_id = ?,
                    completed_by_user_id = ?,
                    completed_at_ms = ?,
                    updated_at_ms = ?
                WHERE review_id = ?
                """,
                (
                    normalized_output,
                    normalized_decision,
                    normalized_follow_up_capa,
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
