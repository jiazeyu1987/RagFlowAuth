from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from backend.database.sqlite import connect_sqlite
from backend.services.users import resolve_login_block

from .types import (
    APPROVAL_RULE_ALL,
    APPROVER_STATUS_APPROVED,
    APPROVER_STATUS_PENDING,
    APPROVER_STATUS_REJECTED,
    INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW,
    REQUEST_STATUS_IN_APPROVAL,
    STEP_STATUS_ACTIVE,
    STEP_STATUS_APPROVED,
    STEP_STATUS_REJECTED,
)


class OperationApprovalMigrationService:
    def __init__(
        self,
        *,
        store: Any,
        user_store: Any,
        deps: Any | None,
        get_user: Callable[[str], Any],
        resolve_user: Callable[[str], Any],
        get_user_by_username: Callable[[str], Any],
        normalize_company_id: Callable[[Any], int | None],
        error_factory: Callable[[str, int], Exception],
        error_type: type[Exception],
    ):
        self._store = store
        self._user_store = user_store
        self._deps = deps
        self._get_user = get_user
        self._resolve_user = resolve_user
        self._get_user_by_username = get_user_by_username
        self._normalize_company_id = normalize_company_id
        self._error_factory = error_factory
        self._error_type = error_type

    def resolve_legacy_actor_user(self, actor: str):
        clean_actor = str(actor or "").strip()
        if not clean_actor:
            return None
        user = self._user_store.get_by_user_id(clean_actor)
        if user is not None:
            return user
        return self._get_user_by_username(clean_actor)

    @staticmethod
    def legacy_step_matches_user(step: dict, user: Any) -> bool:
        blocked, _ = resolve_login_block(user)
        if blocked:
            return False
        conditions: list[bool] = []
        approver_user_id = str(step.get("approver_user_id") or "").strip()
        if approver_user_id:
            conditions.append(str(getattr(user, "user_id", "") or "").strip() == approver_user_id)
        approver_role = str(step.get("approver_role") or "").strip()
        if approver_role:
            conditions.append(str(getattr(user, "role", "") or "").strip() == approver_role)
        approver_group_id = step.get("approver_group_id")
        if approver_group_id is not None:
            user_group_ids = {int(item) for item in (getattr(user, "group_ids", None) or []) if item is not None}
            conditions.append(int(approver_group_id) in user_group_ids)
        approver_department_id = step.get("approver_department_id")
        if approver_department_id is not None:
            user_department_id = getattr(user, "department_id", None)
            conditions.append(user_department_id is not None and int(user_department_id) == int(approver_department_id))
        approver_company_id = step.get("approver_company_id")
        if approver_company_id is not None:
            user_company_id = getattr(user, "company_id", None)
            conditions.append(user_company_id is not None and int(user_company_id) == int(approver_company_id))
        if not conditions:
            return False
        approval_mode = str(step.get("approval_mode") or APPROVAL_RULE_ALL).strip().lower()
        if approval_mode == "any":
            return any(conditions)
        return all(conditions)

    def resolve_legacy_step_approvers(self, *, step: dict, request_company_id: int | None) -> dict[str, dict]:
        resolved: dict[str, dict] = {}
        approver_user_id = str(step.get("approver_user_id") or "").strip()
        if approver_user_id:
            try:
                user = self._resolve_user(approver_user_id)
            except self._error_type:
                user = None
            if user is not None:
                user_company_id = self._normalize_company_id(getattr(user, "company_id", None))
                if request_company_id is None or user_company_id == request_company_id:
                    resolved[str(user.user_id)] = {
                        "approver_user_id": str(user.user_id),
                        "approver_username": str(user.username),
                    }
            return resolved

        list_users = getattr(self._user_store, "list_users", None)
        if not callable(list_users):
            return resolved
        users = list_users(
            role=(str(step.get("approver_role") or "").strip() or None),
            status="active",
            group_id=step.get("approver_group_id"),
            company_id=(step.get("approver_company_id") if step.get("approver_company_id") is not None else request_company_id),
            department_id=step.get("approver_department_id"),
            limit=1000,
        )
        for user in users or []:
            user_company_id = self._normalize_company_id(getattr(user, "company_id", None))
            if request_company_id is not None and user_company_id != request_company_id:
                continue
            if not self.legacy_step_matches_user(step, user):
                continue
            resolved[str(user.user_id)] = {
                "approver_user_id": str(user.user_id),
                "approver_username": str(user.username),
            }
        return resolved

    def import_legacy_document_review(
        self,
        *,
        legacy_instance: dict,
        workflow: dict,
        workflow_steps: list[dict],
        actions: list[dict],
        source_db_path: str,
    ) -> dict:
        doc = getattr(self._deps, "kb_store", None).get_document(str(legacy_instance["doc_id"]))
        if doc is None:
            raise self._error_factory("legacy_review_document_not_found", 409)

        applicant_user_id = str(getattr(doc, "uploaded_by", "") or "").strip()
        if not applicant_user_id:
            raise self._error_factory("legacy_review_applicant_missing", 409)
        applicant_user = self._get_user(applicant_user_id)
        request_company_id = self._normalize_company_id(getattr(applicant_user, "company_id", None))
        current_step_no = int(legacy_instance["current_step_no"])
        action_map: dict[int, list[dict]] = {}
        for action in actions:
            action_map.setdefault(int(action["step_no"]), []).append(action)

        request_steps: list[dict] = []
        for step in workflow_steps:
            step_no = int(step["step_no"])
            resolved = self.resolve_legacy_step_approvers(step=step, request_company_id=request_company_id)
            step_actions = action_map.get(step_no, [])
            for action in step_actions:
                actor_user = self.resolve_legacy_actor_user(str(action.get("actor") or ""))
                if actor_user is None:
                    continue
                resolved.setdefault(
                    str(actor_user.user_id),
                    {
                        "approver_user_id": str(actor_user.user_id),
                        "approver_username": str(actor_user.username),
                    },
                )
            if not resolved:
                raise self._error_factory("legacy_review_migration_unresolved_approvers", 500)

            approvers_by_user_id = {
                user_id: {
                    "approver_user_id": item["approver_user_id"],
                    "approver_username": item.get("approver_username"),
                    "status": APPROVER_STATUS_PENDING,
                    "action": None,
                    "notes": None,
                    "signature_id": None,
                    "acted_at_ms": None,
                }
                for user_id, item in resolved.items()
            }
            for action in step_actions:
                actor_user = self.resolve_legacy_actor_user(str(action.get("actor") or ""))
                if actor_user is None:
                    continue
                approver = approvers_by_user_id.setdefault(
                    str(actor_user.user_id),
                    {
                        "approver_user_id": str(actor_user.user_id),
                        "approver_username": str(actor_user.username),
                        "status": APPROVER_STATUS_PENDING,
                        "action": None,
                        "notes": None,
                        "signature_id": None,
                        "acted_at_ms": None,
                    },
                )
                legacy_action = str(action.get("action") or "").strip().lower()
                if legacy_action == "approve":
                    approver["status"] = APPROVER_STATUS_APPROVED
                    approver["action"] = "approve"
                elif legacy_action == "reject":
                    approver["status"] = APPROVER_STATUS_REJECTED
                    approver["action"] = "reject"
                approver["notes"] = action.get("notes")
                approver["acted_at_ms"] = int(action["created_at_ms"])

            approval_rule = str(step.get("approval_mode") or APPROVAL_RULE_ALL).strip().lower() or APPROVAL_RULE_ALL
            if step_no < current_step_no:
                step_status = STEP_STATUS_APPROVED
            elif step_no == current_step_no:
                step_status = STEP_STATUS_ACTIVE
            else:
                step_status = "pending"
            if any(str(item.get("action") or "") == "reject" for item in step_actions):
                step_status = STEP_STATUS_REJECTED
            request_steps.append(
                {
                    "step_no": step_no,
                    "step_name": str(step["step_name"]),
                    "approval_rule": approval_rule,
                    "status": step_status,
                    "created_at_ms": int(legacy_instance["started_at_ms"]),
                    "activated_at_ms": (
                        int(legacy_instance["started_at_ms"]) if step_no <= current_step_no else None
                    ),
                    "completed_at_ms": (
                        max((int(item["created_at_ms"]) for item in step_actions), default=None)
                        if step_status in {STEP_STATUS_APPROVED, STEP_STATUS_REJECTED}
                        else None
                    ),
                    "approvers": list(approvers_by_user_id.values()),
                }
            )

        request_id = str(uuid4())
        payload = {
            "doc_id": str(doc.doc_id),
            "filename": str(doc.filename),
            "kb_id": str(doc.kb_id),
            "kb_dataset_id": getattr(doc, "kb_dataset_id", None),
            "kb_name": getattr(doc, "kb_name", None),
            "ragflow_doc_id": getattr(doc, "ragflow_doc_id", None),
            "file_path": getattr(doc, "file_path", None),
            "source_db_path": source_db_path,
            "legacy_instance_id": str(legacy_instance["instance_id"]),
            "legacy_workflow_id": str(legacy_instance["workflow_id"]),
        }
        workflow_snapshot = {
            "source": "legacy_document_review",
            "legacy_instance_id": str(legacy_instance["instance_id"]),
            "legacy_workflow_id": str(workflow["workflow_id"]),
            "name": str(workflow["name"]),
            "steps": [
                {
                    "step_no": int(step["step_no"]),
                    "step_name": str(step["step_name"]),
                    "approval_rule": str(step.get("approval_mode") or APPROVAL_RULE_ALL),
                    "approver_user_id": step.get("approver_user_id"),
                    "approver_role": step.get("approver_role"),
                    "approver_group_id": step.get("approver_group_id"),
                    "approver_department_id": step.get("approver_department_id"),
                    "approver_company_id": step.get("approver_company_id"),
                }
                for step in workflow_steps
            ],
        }
        events = [
            {
                "event_type": "request_submitted",
                "actor_user_id": str(applicant_user.user_id),
                "actor_username": str(applicant_user.username),
                "step_no": current_step_no,
                "payload": {
                    "operation_type": INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW,
                    "legacy_instance_id": str(legacy_instance["instance_id"]),
                    "target_ref": str(doc.doc_id),
                    "target_label": str(doc.filename),
                },
                "created_at_ms": int(legacy_instance["started_at_ms"]),
            }
        ]
        for action in actions:
            actor_user = self.resolve_legacy_actor_user(str(action.get("actor") or ""))
            events.append(
                {
                    "event_type": "legacy_action_imported",
                    "actor_user_id": (str(actor_user.user_id) if actor_user is not None else None),
                    "actor_username": (
                        str(actor_user.username) if actor_user is not None else (str(action.get("actor")) if action.get("actor") else None)
                    ),
                    "step_no": int(action["step_no"]),
                    "payload": {
                        "legacy_action": str(action.get("action") or ""),
                        "notes": action.get("notes"),
                    },
                    "created_at_ms": int(action["created_at_ms"]),
                }
            )
        if current_step_no:
            events.append(
                {
                    "event_type": "step_activated",
                    "actor_user_id": str(applicant_user.user_id),
                    "actor_username": str(applicant_user.username),
                    "step_no": current_step_no,
                    "payload": {
                        "current_step_name": next(
                            str(step["step_name"]) for step in request_steps if int(step["step_no"]) == current_step_no
                        )
                    },
                    "created_at_ms": int(legacy_instance["started_at_ms"]),
                }
            )

        imported = self._store.import_request(
            request={
                "request_id": request_id,
                "operation_type": INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW,
                "workflow_name": str(workflow["name"]),
                "status": REQUEST_STATUS_IN_APPROVAL,
                "applicant_user_id": str(applicant_user.user_id),
                "applicant_username": str(applicant_user.username),
                "target_ref": str(doc.doc_id),
                "target_label": str(doc.filename),
                "summary": {
                    "doc_id": str(doc.doc_id),
                    "filename": str(doc.filename),
                    "kb_id": getattr(doc, "kb_name", None) or str(doc.kb_id),
                },
                "payload": payload,
                "result_payload": None,
                "workflow_snapshot": workflow_snapshot,
                "current_step_no": current_step_no,
                "current_step_name": next(
                    str(step["step_name"]) for step in request_steps if int(step["step_no"]) == current_step_no
                ),
                "submitted_at_ms": int(legacy_instance["started_at_ms"]),
                "completed_at_ms": None,
                "execution_started_at_ms": None,
                "executed_at_ms": None,
                "last_error": None,
                "company_id": request_company_id,
                "department_id": self._normalize_company_id(getattr(applicant_user, "department_id", None)),
            },
            steps=request_steps,
            artifacts=[],
            events=events,
        )
        self._store.record_legacy_migration(
            legacy_instance_id=str(legacy_instance["instance_id"]),
            request_id=str(imported["request_id"]),
            company_id=request_company_id,
            source_db_path=source_db_path,
            status="migrated",
            error=None,
        )
        return imported

    def migrate_legacy_document_reviews(self) -> dict:
        kb_store = getattr(self._deps, "kb_store", None)
        source_db_path = str(getattr(kb_store, "db_path", "") or "").strip()
        if not source_db_path:
            return {"migrated": 0, "skipped": 0}
        conn = connect_sqlite(source_db_path)
        try:
            rows = conn.execute(
                """
                SELECT instance_id, doc_id, workflow_id, current_step_no, status, started_at_ms, completed_at_ms
                FROM document_approval_instances
                WHERE status IN ('in_progress', 'pending')
                ORDER BY started_at_ms ASC, instance_id ASC
                """
            ).fetchall()
            migrated = 0
            skipped = 0
            for row in rows:
                legacy_instance_id = str(row["instance_id"])
                existing = self._store.get_legacy_migration(legacy_instance_id=legacy_instance_id)
                if existing and str(existing.get("status") or "") == "migrated":
                    request_id = str(existing.get("request_id") or "").strip()
                    if request_id and self._store.get_request(request_id) is not None:
                        skipped += 1
                        continue

                workflow = conn.execute(
                    """
                    SELECT workflow_id, kb_ref, name, is_active, created_at_ms, updated_at_ms
                    FROM approval_workflows
                    WHERE workflow_id = ?
                    """,
                    (str(row["workflow_id"]),),
                ).fetchone()
                if workflow is None:
                    self._store.record_legacy_migration(
                        legacy_instance_id=legacy_instance_id,
                        request_id=None,
                        company_id=None,
                        source_db_path=source_db_path,
                        status="failed",
                        error="legacy_review_workflow_not_found",
                    )
                    raise self._error_factory("legacy_review_workflow_not_found", 500)

                workflow_steps = conn.execute(
                    """
                    SELECT step_no, step_name, approver_user_id, approver_role, approver_group_id,
                           approver_department_id, approver_company_id, approval_mode
                    FROM approval_workflow_steps
                    WHERE workflow_id = ?
                    ORDER BY step_no ASC
                    """,
                    (str(row["workflow_id"]),),
                ).fetchall()
                actions = conn.execute(
                    """
                    SELECT action_id, step_no, action, actor, notes, created_at_ms
                    FROM document_approval_actions
                    WHERE instance_id = ?
                    ORDER BY created_at_ms ASC, action_id ASC
                    """,
                    (legacy_instance_id,),
                ).fetchall()

                try:
                    self.import_legacy_document_review(
                        legacy_instance={
                            "instance_id": legacy_instance_id,
                            "doc_id": str(row["doc_id"]),
                            "workflow_id": str(row["workflow_id"]),
                            "current_step_no": int(row["current_step_no"] or 0),
                            "status": str(row["status"]),
                            "started_at_ms": int(row["started_at_ms"] or 0),
                            "completed_at_ms": (int(row["completed_at_ms"]) if row["completed_at_ms"] is not None else None),
                        },
                        workflow={
                            "workflow_id": str(workflow["workflow_id"]),
                            "kb_ref": str(workflow["kb_ref"]),
                            "name": str(workflow["name"]),
                        },
                        workflow_steps=[
                            {
                                "step_no": int(item["step_no"] or 0),
                                "step_name": str(item["step_name"]),
                                "approver_user_id": (str(item["approver_user_id"]) if item["approver_user_id"] else None),
                                "approver_role": (str(item["approver_role"]) if item["approver_role"] else None),
                                "approver_group_id": (
                                    int(item["approver_group_id"]) if item["approver_group_id"] is not None else None
                                ),
                                "approver_department_id": (
                                    int(item["approver_department_id"]) if item["approver_department_id"] is not None else None
                                ),
                                "approver_company_id": (
                                    int(item["approver_company_id"]) if item["approver_company_id"] is not None else None
                                ),
                                "approval_mode": str(item["approval_mode"] or APPROVAL_RULE_ALL),
                            }
                            for item in workflow_steps
                        ],
                        actions=[
                            {
                                "action_id": str(item["action_id"]),
                                "step_no": int(item["step_no"] or 0),
                                "action": str(item["action"] or ""),
                                "actor": str(item["actor"] or ""),
                                "notes": item["notes"],
                                "created_at_ms": int(item["created_at_ms"] or 0),
                            }
                            for item in actions
                        ],
                        source_db_path=source_db_path,
                    )
                except Exception as exc:
                    code = str(exc) or exc.__class__.__name__
                    self._store.record_legacy_migration(
                        legacy_instance_id=legacy_instance_id,
                        request_id=None,
                        company_id=None,
                        source_db_path=source_db_path,
                        status="failed",
                        error=code,
                    )
                    if isinstance(exc, self._error_type):
                        raise
                    raise self._error_factory(code, int(getattr(exc, "status_code", 500) or 500)) from exc
                migrated += 1
            return {"migrated": migrated, "skipped": skipped}
        finally:
            conn.close()
