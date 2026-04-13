from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

from backend.database.paths import resolve_auth_db_path
from backend.database.sqlite import connect_sqlite


class ChangeControlServiceError(Exception):
    def __init__(self, code: str, *, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class ChangeControlService:
    def __init__(self, *, db_path: str | None = None, user_inbox_service: Any | None = None):
        self.db_path = resolve_auth_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._user_inbox_service = user_inbox_service

    def _conn(self):
        return connect_sqlite(self.db_path)

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ChangeControlServiceError(f"{field_name}_required")
        return text

    @staticmethod
    def _normalize_string_list(value: Any, field_name: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ChangeControlServiceError(f"{field_name}_invalid")
        items: list[str] = []
        seen: set[str] = set()
        for raw in value:
            clean = str(raw or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            items.append(clean)
        return items

    @staticmethod
    def _serialize_json_field(raw: Any, *, default: Any) -> Any:
        try:
            return json.loads(str(raw)) if raw is not None else default
        except Exception as exc:  # noqa: BLE001
            raise ChangeControlServiceError("change_control_invalid_json_payload", status_code=500) from exc

    @staticmethod
    def _append_action(
        conn,
        *,
        request_id: str,
        action: str,
        actor_user_id: str,
        details: dict[str, Any],
        now_ms: int,
    ) -> None:
        conn.execute(
            """
            INSERT INTO change_request_actions (action_id, request_id, action, actor_user_id, details_json, created_at_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                request_id,
                action,
                actor_user_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True),
                now_ms,
            ),
        )

    def _get_request_row(self, conn, request_id: str):
        row = conn.execute(
            """
            SELECT
                request_id,
                title,
                reason,
                status,
                requester_user_id,
                owner_user_id,
                evaluator_user_id,
                planned_due_date,
                required_departments_json,
                affected_controlled_revisions_json,
                evaluation_summary,
                plan_summary,
                execution_summary,
                close_summary,
                close_outcome,
                ledger_writeback_ref,
                closed_controlled_revisions_json,
                requested_at_ms,
                evaluated_at_ms,
                planned_at_ms,
                execution_started_at_ms,
                execution_completed_at_ms,
                confirmed_at_ms,
                closed_at_ms,
                closed_by_user_id,
                updated_at_ms
            FROM change_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            raise ChangeControlServiceError("change_request_not_found", status_code=404)
        return row

    def _get_plan_items(self, conn, request_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT
                plan_item_id,
                request_id,
                title,
                assignee_user_id,
                due_date,
                status,
                completion_note,
                completed_at_ms,
                created_at_ms,
                updated_at_ms
            FROM change_plan_items
            WHERE request_id = ?
            ORDER BY due_date ASC, created_at_ms ASC, plan_item_id ASC
            """,
            (request_id,),
        ).fetchall()
        return [
            {
                "plan_item_id": str(row["plan_item_id"]),
                "request_id": str(row["request_id"]),
                "title": str(row["title"]),
                "assignee_user_id": str(row["assignee_user_id"]),
                "due_date": str(row["due_date"]),
                "status": str(row["status"]),
                "completion_note": (str(row["completion_note"]) if row["completion_note"] else None),
                "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
                "created_at_ms": int(row["created_at_ms"] or 0),
                "updated_at_ms": int(row["updated_at_ms"] or 0),
            }
            for row in rows
        ]

    def _get_confirmations(self, conn, request_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT confirmation_id, request_id, department_code, confirmed_by_user_id, notes, confirmed_at_ms
            FROM change_confirmations
            WHERE request_id = ?
            ORDER BY confirmed_at_ms ASC, confirmation_id ASC
            """,
            (request_id,),
        ).fetchall()
        return [
            {
                "confirmation_id": str(row["confirmation_id"]),
                "request_id": str(row["request_id"]),
                "department_code": str(row["department_code"]),
                "confirmed_by_user_id": str(row["confirmed_by_user_id"]),
                "notes": (str(row["notes"]) if row["notes"] else None),
                "confirmed_at_ms": int(row["confirmed_at_ms"] or 0),
            }
            for row in rows
        ]

    def _get_actions(self, conn, request_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT action_id, action, actor_user_id, details_json, created_at_ms
            FROM change_request_actions
            WHERE request_id = ?
            ORDER BY created_at_ms ASC, action_id ASC
            """,
            (request_id,),
        ).fetchall()
        return [
            {
                "action_id": str(row["action_id"]),
                "action": str(row["action"]),
                "actor_user_id": str(row["actor_user_id"]),
                "details": self._serialize_json_field(row["details_json"], default={}),
                "created_at_ms": int(row["created_at_ms"] or 0),
            }
            for row in rows
        ]

    def _serialize_request(self, conn, row) -> dict[str, Any]:
        request_id = str(row["request_id"])
        return {
            "request_id": request_id,
            "title": str(row["title"]),
            "reason": str(row["reason"]),
            "status": str(row["status"]),
            "requester_user_id": str(row["requester_user_id"]),
            "owner_user_id": str(row["owner_user_id"]),
            "evaluator_user_id": str(row["evaluator_user_id"]),
            "planned_due_date": (str(row["planned_due_date"]) if row["planned_due_date"] else None),
            "required_departments": self._serialize_json_field(row["required_departments_json"], default=[]),
            "affected_controlled_revisions": self._serialize_json_field(
                row["affected_controlled_revisions_json"], default=[]
            ),
            "evaluation_summary": (str(row["evaluation_summary"]) if row["evaluation_summary"] else None),
            "plan_summary": (str(row["plan_summary"]) if row["plan_summary"] else None),
            "execution_summary": (str(row["execution_summary"]) if row["execution_summary"] else None),
            "close_summary": (str(row["close_summary"]) if row["close_summary"] else None),
            "close_outcome": (str(row["close_outcome"]) if row["close_outcome"] else None),
            "ledger_writeback_ref": (str(row["ledger_writeback_ref"]) if row["ledger_writeback_ref"] else None),
            "closed_controlled_revisions": self._serialize_json_field(
                row["closed_controlled_revisions_json"], default=[]
            )
            if row["closed_controlled_revisions_json"]
            else [],
            "requested_at_ms": int(row["requested_at_ms"] or 0),
            "evaluated_at_ms": (int(row["evaluated_at_ms"]) if row["evaluated_at_ms"] is not None else None),
            "planned_at_ms": (int(row["planned_at_ms"]) if row["planned_at_ms"] is not None else None),
            "execution_started_at_ms": (
                int(row["execution_started_at_ms"]) if row["execution_started_at_ms"] is not None else None
            ),
            "execution_completed_at_ms": (
                int(row["execution_completed_at_ms"]) if row["execution_completed_at_ms"] is not None else None
            ),
            "confirmed_at_ms": (int(row["confirmed_at_ms"]) if row["confirmed_at_ms"] is not None else None),
            "closed_at_ms": (int(row["closed_at_ms"]) if row["closed_at_ms"] is not None else None),
            "closed_by_user_id": (str(row["closed_by_user_id"]) if row["closed_by_user_id"] else None),
            "updated_at_ms": int(row["updated_at_ms"] or 0),
            "plan_items": self._get_plan_items(conn, request_id),
            "confirmations": self._get_confirmations(conn, request_id),
            "actions": self._get_actions(conn, request_id),
        }

    def get_request(self, request_id: str) -> dict[str, Any]:
        conn = self._conn()
        try:
            row = self._get_request_row(conn, self._require_text(request_id, "request_id"))
            return self._serialize_request(conn, row)
        finally:
            conn.close()

    def list_requests(self, *, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 100), 200))
        conn = self._conn()
        try:
            if status:
                rows = conn.execute(
                    """
                    SELECT request_id
                    FROM change_requests
                    WHERE status = ?
                    ORDER BY updated_at_ms DESC, request_id DESC
                    LIMIT ?
                    """,
                    (str(status).strip(), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT request_id
                    FROM change_requests
                    ORDER BY updated_at_ms DESC, request_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [self.get_request(str(row["request_id"])) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _require_role_or_admin(*, row, actor_user_id: str, is_admin: bool, allowed: tuple[str, ...], code: str) -> None:
        if is_admin:
            return
        actor = str(actor_user_id)
        allowed_user_ids = {str(row[field]) for field in allowed}
        if actor not in allowed_user_ids:
            raise ChangeControlServiceError(code, status_code=403)

    def create_request(
        self,
        *,
        title: str,
        reason: str,
        requester_user_id: str,
        owner_user_id: str,
        evaluator_user_id: str,
        planned_due_date: str | None,
        required_departments: list[str],
        affected_controlled_revisions: list[str],
    ) -> dict[str, Any]:
        title = self._require_text(title, "title")
        reason = self._require_text(reason, "reason")
        requester_user_id = self._require_text(requester_user_id, "requester_user_id")
        owner_user_id = self._require_text(owner_user_id, "owner_user_id")
        evaluator_user_id = self._require_text(evaluator_user_id, "evaluator_user_id")
        required_departments = self._normalize_string_list(required_departments, "required_departments")
        affected_controlled_revisions = self._normalize_string_list(
            affected_controlled_revisions, "affected_controlled_revisions"
        )
        request_id = str(uuid4())
        now_ms = int(time.time() * 1000)
        planned_due_date_clean = str(planned_due_date or "").strip() or None
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO change_requests (
                    request_id,
                    title,
                    reason,
                    status,
                    requester_user_id,
                    owner_user_id,
                    evaluator_user_id,
                    planned_due_date,
                    required_departments_json,
                    affected_controlled_revisions_json,
                    requested_at_ms,
                    updated_at_ms
                )
                VALUES (?, ?, ?, 'initiated', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    title,
                    reason,
                    requester_user_id,
                    owner_user_id,
                    evaluator_user_id,
                    planned_due_date_clean,
                    json.dumps(required_departments, ensure_ascii=False, sort_keys=True),
                    json.dumps(affected_controlled_revisions, ensure_ascii=False, sort_keys=True),
                    now_ms,
                    now_ms,
                ),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="initiated",
                actor_user_id=requester_user_id,
                details={
                    "owner_user_id": owner_user_id,
                    "evaluator_user_id": evaluator_user_id,
                    "planned_due_date": planned_due_date_clean,
                    "required_departments": required_departments,
                    "affected_controlled_revisions": affected_controlled_revisions,
                },
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def evaluate_request(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        is_admin: bool,
        evaluation_summary: str,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        evaluation_summary = self._require_text(evaluation_summary, "evaluation_summary")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) != "initiated":
                raise ChangeControlServiceError("change_request_invalid_state", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("evaluator_user_id",),
                code="change_request_evaluator_required",
            )
            conn.execute(
                """
                UPDATE change_requests
                SET status = 'evaluated',
                    evaluation_summary = ?,
                    evaluated_at_ms = ?,
                    updated_at_ms = ?
                WHERE request_id = ?
                """,
                (evaluation_summary, now_ms, now_ms, request_id),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="evaluated",
                actor_user_id=actor_user_id,
                details={"evaluation_summary": evaluation_summary},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def create_plan_item(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        is_admin: bool,
        title: str,
        assignee_user_id: str,
        due_date: str,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        title = self._require_text(title, "title")
        assignee_user_id = self._require_text(assignee_user_id, "assignee_user_id")
        due_date = self._require_text(due_date, "due_date")
        now_ms = int(time.time() * 1000)
        plan_item_id = str(uuid4())
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) not in {"evaluated", "planned", "executing"}:
                raise ChangeControlServiceError("change_request_plan_item_state_invalid", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id", "requester_user_id"),
                code="change_request_plan_owner_required",
            )
            conn.execute(
                """
                INSERT INTO change_plan_items (
                    plan_item_id,
                    request_id,
                    title,
                    assignee_user_id,
                    due_date,
                    status,
                    completion_note,
                    completed_at_ms,
                    created_at_ms,
                    updated_at_ms
                )
                VALUES (?, ?, ?, ?, ?, 'open', NULL, NULL, ?, ?)
                """,
                (plan_item_id, request_id, title, assignee_user_id, due_date, now_ms, now_ms),
            )
            conn.execute("UPDATE change_requests SET updated_at_ms = ? WHERE request_id = ?", (now_ms, request_id))
            self._append_action(
                conn,
                request_id=request_id,
                action="plan_item_added",
                actor_user_id=actor_user_id,
                details={
                    "plan_item_id": plan_item_id,
                    "title": title,
                    "assignee_user_id": assignee_user_id,
                    "due_date": due_date,
                },
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def update_plan_item_status(
        self,
        *,
        request_id: str,
        plan_item_id: str,
        actor_user_id: str,
        is_admin: bool,
        status: str,
        completion_note: str | None = None,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        plan_item_id = self._require_text(plan_item_id, "plan_item_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        status = self._require_text(status, "status").lower()
        if status not in {"open", "completed"}:
            raise ChangeControlServiceError("plan_item_status_invalid")
        note = str(completion_note or "").strip() or None
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id", "requester_user_id"),
                code="change_request_plan_owner_required",
            )
            current_item = conn.execute(
                "SELECT plan_item_id FROM change_plan_items WHERE request_id = ? AND plan_item_id = ?",
                (request_id, plan_item_id),
            ).fetchone()
            if current_item is None:
                raise ChangeControlServiceError("change_plan_item_not_found", status_code=404)
            conn.execute(
                """
                UPDATE change_plan_items
                SET status = ?,
                    completion_note = ?,
                    completed_at_ms = ?,
                    updated_at_ms = ?
                WHERE request_id = ? AND plan_item_id = ?
                """,
                (
                    status,
                    note,
                    (now_ms if status == "completed" else None),
                    now_ms,
                    request_id,
                    plan_item_id,
                ),
            )
            conn.execute("UPDATE change_requests SET updated_at_ms = ? WHERE request_id = ?", (now_ms, request_id))
            self._append_action(
                conn,
                request_id=request_id,
                action="plan_item_status_updated",
                actor_user_id=actor_user_id,
                details={"plan_item_id": plan_item_id, "status": status, "completion_note": note},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def mark_planned(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        is_admin: bool,
        plan_summary: str,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        plan_summary = self._require_text(plan_summary, "plan_summary")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) != "evaluated":
                raise ChangeControlServiceError("change_request_invalid_state", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id",),
                code="change_request_owner_required",
            )
            plan_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM change_plan_items WHERE request_id = ?",
                    (request_id,),
                ).fetchone()["c"]
            )
            if plan_count <= 0:
                raise ChangeControlServiceError("change_request_plan_items_required", status_code=409)
            conn.execute(
                """
                UPDATE change_requests
                SET status = 'planned',
                    plan_summary = ?,
                    planned_at_ms = ?,
                    updated_at_ms = ?
                WHERE request_id = ?
                """,
                (plan_summary, now_ms, now_ms, request_id),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="planned",
                actor_user_id=actor_user_id,
                details={"plan_summary": plan_summary},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def start_execution(self, *, request_id: str, actor_user_id: str, is_admin: bool) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) != "planned":
                raise ChangeControlServiceError("change_request_invalid_state", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id",),
                code="change_request_owner_required",
            )
            conn.execute(
                """
                UPDATE change_requests
                SET status = 'executing',
                    execution_started_at_ms = ?,
                    updated_at_ms = ?
                WHERE request_id = ?
                """,
                (now_ms, now_ms, request_id),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="execution_started",
                actor_user_id=actor_user_id,
                details={},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def complete_execution(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        is_admin: bool,
        execution_summary: str,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        execution_summary = self._require_text(execution_summary, "execution_summary")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) != "executing":
                raise ChangeControlServiceError("change_request_invalid_state", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id",),
                code="change_request_owner_required",
            )
            remaining = int(
                conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM change_plan_items
                    WHERE request_id = ? AND status != 'completed'
                    """,
                    (request_id,),
                ).fetchone()["c"]
            )
            if remaining > 0:
                raise ChangeControlServiceError("change_request_plan_items_incomplete", status_code=409)
            required_departments = self._serialize_json_field(row["required_departments_json"], default=[])
            next_status = "pending_confirmation" if required_departments else "confirmed"
            conn.execute(
                """
                UPDATE change_requests
                SET status = ?,
                    execution_summary = ?,
                    execution_completed_at_ms = ?,
                    confirmed_at_ms = ?,
                    updated_at_ms = ?
                WHERE request_id = ?
                """,
                (
                    next_status,
                    execution_summary,
                    now_ms,
                    (now_ms if next_status == "confirmed" else None),
                    now_ms,
                    request_id,
                ),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="execution_completed",
                actor_user_id=actor_user_id,
                details={"execution_summary": execution_summary, "next_status": next_status},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def confirm_department(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        department_code: str,
        notes: str | None,
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        department_code = self._require_text(department_code, "department_code")
        notes_clean = str(notes or "").strip() or None
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) not in {"pending_confirmation", "confirmed"}:
                raise ChangeControlServiceError("change_request_invalid_state", status_code=409)
            required_departments = self._serialize_json_field(row["required_departments_json"], default=[])
            if not required_departments:
                raise ChangeControlServiceError("change_request_confirmation_not_required", status_code=409)
            if department_code not in required_departments:
                raise ChangeControlServiceError("change_request_department_not_required", status_code=400)
            existing = conn.execute(
                """
                SELECT confirmation_id
                FROM change_confirmations
                WHERE request_id = ? AND department_code = ?
                """,
                (request_id, department_code),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO change_confirmations (
                        confirmation_id, request_id, department_code, confirmed_by_user_id, notes, confirmed_at_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid4()), request_id, department_code, actor_user_id, notes_clean, now_ms),
                )
            else:
                conn.execute(
                    """
                    UPDATE change_confirmations
                    SET confirmed_by_user_id = ?, notes = ?, confirmed_at_ms = ?
                    WHERE request_id = ? AND department_code = ?
                    """,
                    (actor_user_id, notes_clean, now_ms, request_id, department_code),
                )
            confirmed_rows = conn.execute(
                "SELECT department_code FROM change_confirmations WHERE request_id = ?",
                (request_id,),
            ).fetchall()
            confirmed_departments = {str(item["department_code"]) for item in confirmed_rows}
            if all(item in confirmed_departments for item in required_departments):
                conn.execute(
                    """
                    UPDATE change_requests
                    SET status = 'confirmed',
                        confirmed_at_ms = ?,
                        updated_at_ms = ?
                    WHERE request_id = ?
                    """,
                    (now_ms, now_ms, request_id),
                )
            else:
                conn.execute("UPDATE change_requests SET updated_at_ms = ? WHERE request_id = ?", (now_ms, request_id))
            self._append_action(
                conn,
                request_id=request_id,
                action="department_confirmed",
                actor_user_id=actor_user_id,
                details={"department_code": department_code, "notes": notes_clean},
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)

    def dispatch_due_reminders(self, *, actor_user_id: str, window_days: int = 7) -> dict[str, Any]:
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        if self._user_inbox_service is None:
            raise ChangeControlServiceError("change_control_inbox_service_unavailable", status_code=500)
        window_days = max(1, min(int(window_days or 7), 90))
        now_ms = int(time.time() * 1000)
        cutoff_secs = int(time.time()) + window_days * 86400
        cutoff_date = time.strftime("%Y-%m-%d", time.localtime(cutoff_secs))
        conn = self._conn()
        try:
            rows = conn.execute(
                """
                SELECT
                    i.plan_item_id,
                    i.request_id,
                    i.title AS plan_title,
                    i.assignee_user_id,
                    i.due_date,
                    r.title AS request_title,
                    r.status AS request_status
                FROM change_plan_items i
                JOIN change_requests r ON r.request_id = i.request_id
                WHERE i.status = 'open'
                  AND i.due_date <= ?
                  AND r.status IN ('planned', 'executing', 'pending_confirmation')
                ORDER BY i.due_date ASC, i.plan_item_id ASC
                """,
                (cutoff_date,),
            ).fetchall()
            reminders: list[dict[str, Any]] = []
            for row in rows:
                payload = {
                    "request_id": str(row["request_id"]),
                    "plan_item_id": str(row["plan_item_id"]),
                    "due_date": str(row["due_date"]),
                    "request_status": str(row["request_status"]),
                }
                created = self._user_inbox_service.notify_users(
                    recipients=[{"user_id": str(row["assignee_user_id"])}],
                    title=f"变更计划即将到期: {str(row['request_title'])}",
                    body=f"{str(row['plan_title'])} 需在 {str(row['due_date'])} 前完成",
                    event_type="change_control_due_soon",
                    link_path=f"/quality-system/change-control?request_id={str(row['request_id'])}",
                    payload=payload,
                )
                reminders.append(
                    {
                        "request_id": str(row["request_id"]),
                        "plan_item_id": str(row["plan_item_id"]),
                        "assignee_user_id": str(row["assignee_user_id"]),
                        "due_date": str(row["due_date"]),
                        "inbox_items_created": len(created),
                    }
                )
            return {"window_days": window_days, "count": len(reminders), "items": reminders, "dispatched_at_ms": now_ms}
        finally:
            conn.close()

    def close_request(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        is_admin: bool,
        close_summary: str,
        close_outcome: str,
        ledger_writeback_ref: str,
        closed_controlled_revisions: list[str],
    ) -> dict[str, Any]:
        request_id = self._require_text(request_id, "request_id")
        actor_user_id = self._require_text(actor_user_id, "actor_user_id")
        close_summary = self._require_text(close_summary, "close_summary")
        close_outcome = self._require_text(close_outcome, "close_outcome")
        ledger_writeback_ref = self._require_text(ledger_writeback_ref, "ledger_writeback_ref")
        closed_controlled_revisions = self._normalize_string_list(
            closed_controlled_revisions, "closed_controlled_revisions"
        )
        if not closed_controlled_revisions:
            raise ChangeControlServiceError("closed_controlled_revisions_required")
        now_ms = int(time.time() * 1000)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = self._get_request_row(conn, request_id)
            if str(row["status"]) != "confirmed":
                raise ChangeControlServiceError("change_request_must_be_confirmed_before_close", status_code=409)
            self._require_role_or_admin(
                row=row,
                actor_user_id=actor_user_id,
                is_admin=is_admin,
                allowed=("owner_user_id", "requester_user_id"),
                code="change_request_owner_required",
            )
            conn.execute(
                """
                UPDATE change_requests
                SET status = 'closed',
                    close_summary = ?,
                    close_outcome = ?,
                    ledger_writeback_ref = ?,
                    closed_controlled_revisions_json = ?,
                    closed_at_ms = ?,
                    closed_by_user_id = ?,
                    updated_at_ms = ?
                WHERE request_id = ?
                """,
                (
                    close_summary,
                    close_outcome,
                    ledger_writeback_ref,
                    json.dumps(closed_controlled_revisions, ensure_ascii=False, sort_keys=True),
                    now_ms,
                    actor_user_id,
                    now_ms,
                    request_id,
                ),
            )
            self._append_action(
                conn,
                request_id=request_id,
                action="closed",
                actor_user_id=actor_user_id,
                details={
                    "close_summary": close_summary,
                    "close_outcome": close_outcome,
                    "ledger_writeback_ref": ledger_writeback_ref,
                    "closed_controlled_revisions": closed_controlled_revisions,
                },
                now_ms=now_ms,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return self.get_request(request_id)
