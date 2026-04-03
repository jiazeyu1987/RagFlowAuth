from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class EmergencyChangeServiceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


FIELD_REQUIRED_CODES = {
    "authorization_basis": "authorization_basis_required",
    "risk_control": "risk_control_required",
    "impact_assessment_summary": "impact_assessment_summary_required",
    "post_review_summary": "post_review_summary_required",
    "capa_actions": "capa_actions_required",
    "verification_summary": "verification_summary_required",
}


class EmergencyChangeService:
    def __init__(self, db_path: str | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise EmergencyChangeServiceError(FIELD_REQUIRED_CODES.get(field_name, f"{field_name}_required"), status_code=400)
        return text

    @staticmethod
    def _serialize_action(row) -> dict[str, Any]:
        return {
            "action_id": str(row["action_id"]),
            "action": str(row["action"]),
            "actor_user_id": str(row["actor_user_id"]),
            "details": json.loads(str(row["details_json"]) or "{}"),
            "created_at_ms": int(row["created_at_ms"] or 0),
        }

    def _serialize_change(self, row, *, actions: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "change_id": str(row["change_id"]),
            "title": str(row["title"]),
            "summary": str(row["summary"]),
            "status": str(row["status"]),
            "requested_by_user_id": str(row["requested_by_user_id"]),
            "authorizer_user_id": str(row["authorizer_user_id"]),
            "reviewer_user_id": str(row["reviewer_user_id"]),
            "authorization_basis": str(row["authorization_basis"]),
            "risk_assessment": str(row["risk_assessment"]),
            "risk_control": str(row["risk_control"]),
            "rollback_plan": str(row["rollback_plan"]),
            "training_notification_plan": str(row["training_notification_plan"]),
            "authorization_notes": (str(row["authorization_notes"]) if row["authorization_notes"] else None),
            "deployment_summary": (str(row["deployment_summary"]) if row["deployment_summary"] else None),
            "impact_assessment_summary": (
                str(row["impact_assessment_summary"]) if row["impact_assessment_summary"] else None
            ),
            "post_review_summary": (str(row["post_review_summary"]) if row["post_review_summary"] else None),
            "capa_actions": (str(row["capa_actions"]) if row["capa_actions"] else None),
            "verification_summary": (str(row["verification_summary"]) if row["verification_summary"] else None),
            "requested_at_ms": int(row["requested_at_ms"] or 0),
            "authorized_at_ms": (int(row["authorized_at_ms"]) if row["authorized_at_ms"] is not None else None),
            "deployed_at_ms": (int(row["deployed_at_ms"]) if row["deployed_at_ms"] is not None else None),
            "closed_at_ms": (int(row["closed_at_ms"]) if row["closed_at_ms"] is not None else None),
            "authorized_by_user_id": (
                str(row["authorized_by_user_id"]) if row["authorized_by_user_id"] else None
            ),
            "deployed_by_user_id": (str(row["deployed_by_user_id"]) if row["deployed_by_user_id"] else None),
            "closed_by_user_id": (str(row["closed_by_user_id"]) if row["closed_by_user_id"] else None),
            "actions": actions,
        }

    def _get_change_row(self, conn, change_id: str):
        row = conn.execute(
            """
            SELECT
                change_id,
                title,
                summary,
                status,
                requested_by_user_id,
                authorizer_user_id,
                reviewer_user_id,
                authorization_basis,
                risk_assessment,
                risk_control,
                rollback_plan,
                training_notification_plan,
                authorization_notes,
                deployment_summary,
                impact_assessment_summary,
                post_review_summary,
                capa_actions,
                verification_summary,
                requested_at_ms,
                authorized_at_ms,
                deployed_at_ms,
                closed_at_ms,
                authorized_by_user_id,
                deployed_by_user_id,
                closed_by_user_id
            FROM emergency_changes
            WHERE change_id = ?
            """,
            (change_id,),
        ).fetchone()
        if row is None:
            raise EmergencyChangeServiceError("emergency_change_not_found", status_code=404)
        return row

    def _get_actions(self, conn, change_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT action_id, action, actor_user_id, details_json, created_at_ms
            FROM emergency_change_actions
            WHERE change_id = ?
            ORDER BY created_at_ms ASC, action_id ASC
            """,
            (change_id,),
        ).fetchall()
        return [self._serialize_action(row) for row in rows]

    @staticmethod
    def _append_action(conn, *, change_id: str, action: str, actor_user_id: str, details: dict[str, Any], now_ms: int) -> None:
        conn.execute(
            """
            INSERT INTO emergency_change_actions (action_id, change_id, action, actor_user_id, details_json, created_at_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                change_id,
                action,
                actor_user_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True),
                now_ms,
            ),
        )

    def get_change(self, change_id: str) -> dict[str, Any]:
        conn = self._conn()
        try:
            row = self._get_change_row(conn, self._require_text(change_id, "change_id"))
            return self._serialize_change(row, actions=self._get_actions(conn, str(row["change_id"])))
        finally:
            conn.close()

    def list_changes(self, *, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    """
                    SELECT change_id
                    FROM emergency_changes
                    WHERE status = ?
                    ORDER BY requested_at_ms DESC, change_id DESC
                    LIMIT ?
                    """,
                    (str(status).strip(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT change_id
                    FROM emergency_changes
                    ORDER BY requested_at_ms DESC, change_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self.get_change(str(row["change_id"])) for row in rows]
        finally:
            conn.close()

    def create_change(
        self,
        *,
        title: str,
        summary: str,
        requested_by_user_id: str,
        authorizer_user_id: str,
        reviewer_user_id: str,
        authorization_basis: str,
        risk_assessment: str,
        risk_control: str,
        rollback_plan: str,
        training_notification_plan: str,
    ) -> dict[str, Any]:
        title = self._require_text(title, "title")
        summary = self._require_text(summary, "summary")
        requested_by_user_id = self._require_text(requested_by_user_id, "requested_by_user_id")
        authorizer_user_id = self._require_text(authorizer_user_id, "authorizer_user_id")
        reviewer_user_id = self._require_text(reviewer_user_id, "reviewer_user_id")
        authorization_basis = self._require_text(authorization_basis, "authorization_basis")
        risk_assessment = self._require_text(risk_assessment, "risk_assessment")
        risk_control = self._require_text(risk_control, "risk_control")
        rollback_plan = self._require_text(rollback_plan, "rollback_plan")
        training_notification_plan = self._require_text(training_notification_plan, "training_notification_plan")

        change_id = str(uuid4())
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO emergency_changes (
                    change_id,
                    title,
                    summary,
                    status,
                    requested_by_user_id,
                    authorizer_user_id,
                    reviewer_user_id,
                    authorization_basis,
                    risk_assessment,
                    risk_control,
                    rollback_plan,
                    training_notification_plan,
                    requested_at_ms
                )
                VALUES (?, ?, ?, 'requested', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    change_id,
                    title,
                    summary,
                    requested_by_user_id,
                    authorizer_user_id,
                    reviewer_user_id,
                    authorization_basis,
                    risk_assessment,
                    risk_control,
                    rollback_plan,
                    training_notification_plan,
                    now_ms,
                ),
            )
            self._append_action(
                conn,
                change_id=change_id,
                action="requested",
                actor_user_id=requested_by_user_id,
                details={
                    "title": title,
                    "authorizer_user_id": authorizer_user_id,
                    "reviewer_user_id": reviewer_user_id,
                },
                now_ms=now_ms,
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_change(change_id)

    def authorize_change(self, *, change_id: str, actor_user_id: str, authorization_notes: str | None = None) -> dict[str, Any]:
        change_id = self._require_text(change_id, "change_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        notes = str(authorization_notes or "").strip() or None
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_change_row(conn, change_id)
            if str(row["status"]) != "requested":
                raise EmergencyChangeServiceError("emergency_change_invalid_state", status_code=409)
            if str(row["authorizer_user_id"]) != actor_user_id:
                raise EmergencyChangeServiceError("emergency_change_authorizer_required", status_code=403)
            conn.execute(
                """
                UPDATE emergency_changes
                SET status = 'authorized',
                    authorization_notes = ?,
                    authorized_at_ms = ?,
                    authorized_by_user_id = ?
                WHERE change_id = ?
                """,
                (notes, now_ms, actor_user_id, change_id),
            )
            self._append_action(
                conn,
                change_id=change_id,
                action="authorized",
                actor_user_id=actor_user_id,
                details={"authorization_notes": notes},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_change(change_id)

    def deploy_change(self, *, change_id: str, actor_user_id: str, deployment_summary: str) -> dict[str, Any]:
        change_id = self._require_text(change_id, "change_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        deployment_summary = self._require_text(deployment_summary, "deployment_summary")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_change_row(conn, change_id)
            if str(row["status"]) != "authorized":
                raise EmergencyChangeServiceError("emergency_change_must_be_authorized_before_deploy", status_code=409)
            conn.execute(
                """
                UPDATE emergency_changes
                SET status = 'deployed',
                    deployment_summary = ?,
                    deployed_at_ms = ?,
                    deployed_by_user_id = ?
                WHERE change_id = ?
                """,
                (deployment_summary, now_ms, actor_user_id, change_id),
            )
            self._append_action(
                conn,
                change_id=change_id,
                action="deployed",
                actor_user_id=actor_user_id,
                details={"deployment_summary": deployment_summary},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_change(change_id)

    def close_change(
        self,
        *,
        change_id: str,
        actor_user_id: str,
        impact_assessment_summary: str,
        post_review_summary: str,
        capa_actions: str,
        verification_summary: str,
    ) -> dict[str, Any]:
        change_id = self._require_text(change_id, "change_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        impact_assessment_summary = self._require_text(impact_assessment_summary, "impact_assessment_summary")
        post_review_summary = self._require_text(post_review_summary, "post_review_summary")
        capa_actions = self._require_text(capa_actions, "capa_actions")
        verification_summary = self._require_text(verification_summary, "verification_summary")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_change_row(conn, change_id)
            if str(row["status"]) != "deployed":
                raise EmergencyChangeServiceError("emergency_change_must_be_deployed_before_close", status_code=409)
            if str(row["reviewer_user_id"]) != actor_user_id:
                raise EmergencyChangeServiceError("emergency_change_reviewer_required", status_code=403)
            conn.execute(
                """
                UPDATE emergency_changes
                SET status = 'closed',
                    impact_assessment_summary = ?,
                    post_review_summary = ?,
                    capa_actions = ?,
                    verification_summary = ?,
                    closed_at_ms = ?,
                    closed_by_user_id = ?
                WHERE change_id = ?
                """,
                (
                    impact_assessment_summary,
                    post_review_summary,
                    capa_actions,
                    verification_summary,
                    now_ms,
                    actor_user_id,
                    change_id,
                ),
            )
            self._append_action(
                conn,
                change_id=change_id,
                action="closed",
                actor_user_id=actor_user_id,
                details={
                    "impact_assessment_summary": impact_assessment_summary,
                    "post_review_summary": post_review_summary,
                    "capa_actions": capa_actions,
                    "verification_summary": verification_summary,
                },
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_change(change_id)
