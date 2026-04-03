from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.services.users import resolve_login_block

from .store import ApprovalWorkflowStore

logger = logging.getLogger(__name__)


@dataclass
class ApprovalWorkflowError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class ApprovalWorkflowService:
    def __init__(
        self,
        store: ApprovalWorkflowStore,
        notification_manager: Any | None = None,
        notification_service: Any | None = None,
        user_store: Any | None = None,
    ):
        self._store = store
        self._notification_manager = notification_manager or notification_service
        self._user_store = user_store

    def upsert_workflow(
        self,
        *,
        workflow_id: str,
        kb_ref: str,
        name: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if len(steps or []) < 2:
            raise ApprovalWorkflowError("workflow_min_two_steps", status_code=400)
        try:
            return self._store.upsert_workflow(
                workflow_id=workflow_id,
                kb_ref=kb_ref,
                name=name,
                steps=steps,
                is_active=True,
            )
        except ValueError as e:
            raise ApprovalWorkflowError(str(e), status_code=400) from e

    def list_workflows(self, *, kb_ref: str | None = None) -> list[dict[str, Any]]:
        return self._store.list_workflows(kb_ref=kb_ref)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        item = self._store.get_workflow(workflow_id)
        if not item:
            raise ApprovalWorkflowError("workflow_not_found", status_code=404)
        return item

    @staticmethod
    def _effective_user_group_ids(user: Any) -> set[int]:
        values: set[int] = set()
        raw_group_id = getattr(user, "group_id", None)
        if raw_group_id is not None:
            values.add(int(raw_group_id))
        for raw_value in getattr(user, "group_ids", None) or []:
            if raw_value is None:
                continue
            values.add(int(raw_value))
        return values

    @classmethod
    def _step_matches_user(cls, step: dict[str, Any], user: Any) -> bool:
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
            conditions.append(int(approver_group_id) in cls._effective_user_group_ids(user))

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
        approval_mode = str(step.get("approval_mode") or "all").strip().lower()
        if approval_mode == "any":
            return any(conditions)
        return all(conditions)

    @staticmethod
    def _kb_refs_from_doc(doc: Any) -> list[str]:
        out: list[str] = []
        for key in ("kb_dataset_id", "kb_name", "kb_id"):
            value = str(getattr(doc, key, "") or "").strip()
            if value and value not in out:
                out.append(value)
        return out

    def _resolve_progress(self, doc: Any, *, create_instance: bool = True) -> dict[str, Any]:
        refs = self._kb_refs_from_doc(doc)
        workflow = self._store.find_active_workflow_by_refs(refs)
        if not workflow:
            raise ApprovalWorkflowError("approval_workflow_not_configured", status_code=400)
        steps = workflow.get("steps") or []
        if not steps:
            raise ApprovalWorkflowError("approval_workflow_no_steps", status_code=400)

        instance = self._store.get_instance_by_doc_id(doc.doc_id)
        if not instance:
            if create_instance:
                instance = self._store.create_instance(doc_id=doc.doc_id, workflow_id=workflow["workflow_id"])
            else:
                instance = {
                    "instance_id": None,
                    "doc_id": str(doc.doc_id),
                    "workflow_id": str(workflow["workflow_id"]),
                    "current_step_no": 1,
                    "status": "in_progress",
                    "started_at_ms": None,
                    "completed_at_ms": None,
                }
        if str(instance.get("workflow_id")) != str(workflow["workflow_id"]):
            raise ApprovalWorkflowError("approval_workflow_instance_mismatch", status_code=409)

        max_step_no = max(int(s["step_no"]) for s in steps)
        current_step_no = int(instance.get("current_step_no") or 0)
        step_map = {int(s["step_no"]): s for s in steps}
        current_step = step_map.get(current_step_no)
        if current_step is None:
            raise ApprovalWorkflowError("approval_workflow_invalid_current_step", status_code=409)
        return {
            "workflow": workflow,
            "instance": instance,
            "max_step_no": max_step_no,
            "current_step_no": current_step_no,
            "current_step_name": str(current_step["step_name"]),
            "current_step": current_step,
            "next_step_name": (
                str(step_map[current_step_no + 1]["step_name"]) if (current_step_no + 1) in step_map else None
            ),
        }

    def get_instance_brief(self, doc_id: str) -> dict[str, Any] | None:
        instance = self._store.get_instance_by_doc_id(doc_id)
        if not instance:
            return None
        workflow = self._store.get_workflow(str(instance["workflow_id"]))
        if not workflow:
            return None
        step_map = {int(s["step_no"]): str(s["step_name"]) for s in (workflow.get("steps") or [])}
        return {
            "approval_status": instance["status"],
            "current_step_no": int(instance["current_step_no"] or 0),
            "current_step_name": step_map.get(int(instance["current_step_no"] or 0)),
            "workflow_id": workflow["workflow_id"],
            "workflow_name": workflow["name"],
        }

    def can_user_review_current_step(self, *, doc: Any, user: Any) -> bool:
        try:
            progress = self._resolve_progress(doc, create_instance=False)
        except ApprovalWorkflowError:
            return False
        return self._step_matches_user(progress["current_step"], user)

    def get_pending_reviews_for_user(self, *, docs: list[Any], user: Any) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for doc in docs:
            try:
                progress = self._resolve_progress(doc, create_instance=False)
            except ApprovalWorkflowError:
                continue
            if str(progress["instance"].get("status")) not in ("in_progress", "pending"):
                continue
            if not self._step_matches_user(progress["current_step"], user):
                continue
            items.append(
                {
                    "doc_id": str(getattr(doc, "doc_id", "") or ""),
                    "filename": str(getattr(doc, "filename", "") or ""),
                    "kb_id": str(getattr(doc, "kb_id", "") or ""),
                    "kb_dataset_id": str(getattr(doc, "kb_dataset_id", "") or ""),
                    "kb_name": str(getattr(doc, "kb_name", "") or ""),
                    "uploaded_by": str(getattr(doc, "uploaded_by", "") or ""),
                    "uploaded_at_ms": int(getattr(doc, "uploaded_at_ms", 0) or 0),
                    "workflow_id": str(progress["workflow"]["workflow_id"]),
                    "workflow_name": str(progress["workflow"]["name"]),
                    "current_step_no": int(progress["current_step_no"]),
                    "current_step_name": str(progress["current_step_name"]),
                    "approval_status": str(progress["instance"]["status"]),
                }
            )
        return items

    def notify_current_step(self, *, doc: Any, actor: str | None = None, notes: str | None = None) -> None:
        if self._notification_manager is None:
            return
        try:
            progress = self._resolve_progress(doc)
            brief = self.get_instance_brief(str(doc.doc_id))
            if not brief:
                raise ApprovalWorkflowError("approval_instance_missing_after_update", status_code=500)
            recipients = self._step_recipients(progress["current_step"])
        except Exception as e:
            logger.warning(
                "Approval notification preparation failed without blocking transaction: doc_id=%s err=%s",
                getattr(doc, "doc_id", None),
                e,
            )
            return
        self._notify_non_blocking(
            event_type="review_todo_approval",
            payload=self._notification_payload(
                doc=doc,
                actor=(actor or ""),
                notes=notes,
                brief=brief,
                action="pending_approval",
                final=False,
            ),
            recipients=recipients,
            dedupe_key=self._dedupe_key(
                event_type="review_todo_approval",
                doc=doc,
                brief=brief,
            ),
        )

    def approve_step(self, *, doc: Any, actor: str, actor_user: Any, notes: str | None, final: bool) -> dict[str, Any]:
        progress = self._resolve_progress(doc)
        instance = progress["instance"]
        current_step_no = int(progress["current_step_no"])
        max_step_no = int(progress["max_step_no"])
        if str(instance.get("status")) not in ("in_progress", "pending"):
            raise ApprovalWorkflowError("approval_instance_not_active", status_code=409)
        if not self._step_matches_user(progress["current_step"], actor_user):
            raise ApprovalWorkflowError("approval_actor_not_assigned_to_step", status_code=403)
        if final and current_step_no != max_step_no:
            raise ApprovalWorkflowError("approval_step_not_final", status_code=409)
        if (not final) and current_step_no >= max_step_no:
            raise ApprovalWorkflowError("approval_step_already_final", status_code=409)

        self._store.record_action(
            instance_id=str(instance["instance_id"]),
            doc_id=str(doc.doc_id),
            workflow_id=str(instance["workflow_id"]),
            step_no=current_step_no,
            action="approve",
            actor=actor,
            notes=notes,
        )
        if final:
            self._store.complete_instance(instance_id=str(instance["instance_id"]), status="approved")
        else:
            self._store.advance_instance(instance_id=str(instance["instance_id"]), next_step_no=current_step_no + 1)
        brief = self.get_instance_brief(str(doc.doc_id))
        if not brief:
            raise ApprovalWorkflowError("approval_instance_missing_after_update", status_code=500)
        if final:
            self._notify_outcome(
                event_type="review_approved",
                doc=doc,
                actor=actor,
                notes=notes,
                brief=brief,
                action="approve",
            )
        else:
            self.notify_current_step(doc=doc, actor=actor, notes=notes)
        return brief

    def reject_step(self, *, doc: Any, actor: str, actor_user: Any, notes: str | None) -> dict[str, Any]:
        progress = self._resolve_progress(doc)
        instance = progress["instance"]
        current_step_no = int(progress["current_step_no"])
        if str(instance.get("status")) not in ("in_progress", "pending"):
            raise ApprovalWorkflowError("approval_instance_not_active", status_code=409)
        if not self._step_matches_user(progress["current_step"], actor_user):
            raise ApprovalWorkflowError("approval_actor_not_assigned_to_step", status_code=403)

        self._store.record_action(
            instance_id=str(instance["instance_id"]),
            doc_id=str(doc.doc_id),
            workflow_id=str(instance["workflow_id"]),
            step_no=current_step_no,
            action="reject",
            actor=actor,
            notes=notes,
        )
        self._store.complete_instance(instance_id=str(instance["instance_id"]), status="rejected")
        brief = self.get_instance_brief(str(doc.doc_id))
        if not brief:
            raise ApprovalWorkflowError("approval_instance_missing_after_update", status_code=500)
        self._notify_outcome(
            event_type="review_rejected",
            doc=doc,
            actor=actor,
            notes=notes,
            brief=brief,
            action="reject",
        )
        return brief

    def approval_progress(self, *, doc: Any, user: Any | None = None, create_instance: bool = True) -> dict[str, Any]:
        progress = self._resolve_progress(doc, create_instance=create_instance)
        return {
            "workflow_id": progress["workflow"]["workflow_id"],
            "workflow_name": progress["workflow"]["name"],
            "approval_status": progress["instance"]["status"],
            "current_step_no": progress["current_step_no"],
            "current_step_name": progress["current_step_name"],
            "max_step_no": progress["max_step_no"],
            "is_final_step": progress["current_step_no"] >= progress["max_step_no"],
            "next_step_name": progress["next_step_name"],
            "can_review_current_step": (self._step_matches_user(progress["current_step"], user) if user else None),
        }

    @staticmethod
    def _notification_payload(
        *,
        doc: Any,
        actor: str,
        notes: str | None,
        brief: dict[str, Any],
        action: str,
        final: bool,
    ) -> dict[str, Any]:
        return {
            "doc_id": str(getattr(doc, "doc_id", "") or ""),
            "filename": str(getattr(doc, "filename", "") or ""),
            "kb_id": str(getattr(doc, "kb_id", "") or ""),
            "kb_dataset_id": str(getattr(doc, "kb_dataset_id", "") or ""),
            "kb_name": str(getattr(doc, "kb_name", "") or ""),
            "workflow_id": str(brief.get("workflow_id") or ""),
            "workflow_name": str(brief.get("workflow_name") or ""),
            "approval_status": str(brief.get("approval_status") or ""),
            "current_step_no": int(brief.get("current_step_no") or 0),
            "current_step_name": brief.get("current_step_name"),
            "actor": str(actor or ""),
            "notes": notes,
            "action": action,
            "final": bool(final),
            "approval_target": {
                "doc_id": str(getattr(doc, "doc_id", "") or ""),
                "kb_id": str(getattr(doc, "kb_id", "") or ""),
                "workflow_id": str(brief.get("workflow_id") or ""),
                "workflow_name": str(brief.get("workflow_name") or ""),
                "step_no": int(brief.get("current_step_no") or 0),
                "step_name": brief.get("current_step_name"),
                "route_path": f"/documents?tab=approve&doc_id={str(getattr(doc, 'doc_id', '') or '')}",
            },
        }

    def _notify_non_blocking(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        recipients: list[dict[str, Any]],
        dedupe_key: str,
    ) -> None:
        service = self._notification_manager
        if service is None:
            return
        try:
            service.notify_event(
                event_type=event_type,
                payload=payload,
                recipients=recipients,
                dedupe_key=dedupe_key,
            )
            service.dispatch_pending(limit=20)
        except Exception as e:
            # T06 requirement: notification delivery must not block main approval transaction.
            logger.warning(
                "Approval notification failed without blocking transaction: event_type=%s err=%s",
                event_type,
                e,
            )

    def _notify_outcome(
        self,
        *,
        event_type: str,
        doc: Any,
        actor: str,
        notes: str | None,
        brief: dict[str, Any],
        action: str,
    ) -> None:
        recipients = self._uploader_recipients(doc)
        if not recipients:
            return
        self._notify_non_blocking(
            event_type=event_type,
            payload=self._notification_payload(
                doc=doc,
                actor=actor,
                notes=notes,
                brief=brief,
                action=action,
                final=True,
            ),
            recipients=recipients,
            dedupe_key=self._dedupe_key(event_type=event_type, doc=doc, brief=brief),
        )

    def _step_recipients(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        if self._user_store is None:
            raise ApprovalWorkflowError("approval_notification_user_store_unavailable", status_code=500)
        users = self._user_store.list_users(
            role=(step.get("approver_role") or None),
            status="active",
            group_id=step.get("approver_group_id"),
            company_id=step.get("approver_company_id"),
            department_id=step.get("approver_department_id"),
            limit=1000,
        )
        recipients = [self._user_notification_fields(user) for user in users if self._step_matches_user(step, user)]
        if not recipients:
            raise ApprovalWorkflowError("approval_notification_recipient_missing", status_code=409)
        return recipients

    def _uploader_recipients(self, doc: Any) -> list[dict[str, Any]]:
        if self._user_store is None:
            return []
        uploaded_by = str(getattr(doc, "uploaded_by", "") or "").strip()
        if not uploaded_by:
            return []
        user = self._user_store.get_by_user_id(uploaded_by)
        if user is None:
            return []
        return [self._user_notification_fields(user)]

    @staticmethod
    def _user_notification_fields(user: Any) -> dict[str, Any]:
        return {
            "user_id": str(getattr(user, "user_id", "") or "").strip() or None,
            "username": str(getattr(user, "username", "") or "").strip() or None,
            "full_name": str(getattr(user, "full_name", "") or "").strip() or None,
            "email": str(getattr(user, "email", "") or "").strip() or None,
        }

    @staticmethod
    def _dedupe_key(*, event_type: str, doc: Any, brief: dict[str, Any]) -> str:
        return ":".join(
            [
                str(event_type or "").strip(),
                str(getattr(doc, "doc_id", "") or "").strip(),
                str(brief.get("workflow_id") or "").strip(),
                str(int(brief.get("current_step_no") or 0)),
                str(brief.get("approval_status") or "").strip(),
            ]
        )
