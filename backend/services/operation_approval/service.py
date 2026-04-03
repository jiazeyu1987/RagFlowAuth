from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from backend.services.audit_helpers import actor_fields_from_ctx, actor_fields_from_user
from backend.services.electronic_signature import ElectronicSignatureError

from .handlers import HANDLER_REGISTRY
from .store import OperationApprovalStore
from .types import (
    APPROVER_STATUS_APPROVED,
    APPROVER_STATUS_PENDING,
    APPROVER_STATUS_REJECTED,
    OPERATION_TYPE_LABELS,
    REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    REQUEST_STATUS_EXECUTING,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
    STEP_STATUS_ACTIVE,
    STEP_STATUS_APPROVED,
    STEP_STATUS_REJECTED,
    SUPPORTED_OPERATION_TYPES,
)


@dataclass
class OperationApprovalServiceError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class OperationApprovalService:
    def __init__(
        self,
        *,
        store: OperationApprovalStore,
        user_store: Any,
        inbox_service: Any | None = None,
        notification_service: Any | None = None,
        electronic_signature_service: Any | None = None,
        deps: Any | None = None,
    ):
        self._store = store
        self._user_store = user_store
        self._inbox_service = inbox_service
        self._notification_service = notification_service
        self._signature_service = electronic_signature_service
        self._deps = deps

    @staticmethod
    def operation_label(operation_type: str) -> str:
        return OPERATION_TYPE_LABELS.get(operation_type, operation_type)

    def _require_supported_operation_type(self, operation_type: str) -> str:
        value = str(operation_type or "").strip()
        if value not in SUPPORTED_OPERATION_TYPES:
            raise OperationApprovalServiceError("operation_type_unsupported", status_code=400)
        return value

    def _get_user(self, user_id: str):
        user = self._user_store.get_by_user_id(user_id)
        if not user:
            raise OperationApprovalServiceError("workflow_approver_not_found", status_code=400)
        return user

    def _resolve_user(self, user_id: str):
        user = self._get_user(user_id)
        if str(getattr(user, "status", "") or "").strip().lower() != "active":
            raise OperationApprovalServiceError("workflow_approver_inactive", status_code=400)
        return user

    def _build_workflow_steps(self, *, steps: list[dict]) -> list[dict]:
        if not steps:
            raise OperationApprovalServiceError("workflow_steps_required", status_code=400)
        normalized: list[dict] = []
        for index, item in enumerate(steps, start=1):
            step_name = str((item or {}).get("step_name") or "").strip()
            if not step_name:
                raise OperationApprovalServiceError("workflow_step_name_required", status_code=400)
            raw_user_ids = (item or {}).get("approver_user_ids") or []
            if not isinstance(raw_user_ids, list):
                raise OperationApprovalServiceError("workflow_step_approvers_required", status_code=400)
            approver_user_ids: list[str] = []
            for raw_user_id in raw_user_ids:
                user_id = str(raw_user_id or "").strip()
                if not user_id:
                    continue
                if user_id in approver_user_ids:
                    raise OperationApprovalServiceError("workflow_step_duplicate_approver", status_code=400)
                self._resolve_user(user_id)
                approver_user_ids.append(user_id)
            if not approver_user_ids:
                raise OperationApprovalServiceError("workflow_step_approvers_required", status_code=400)
            normalized.append({"step_no": index, "step_name": step_name, "approver_user_ids": approver_user_ids})
        return normalized

    def _enrich_workflow(self, workflow: dict) -> dict:
        item = dict(workflow)
        item["operation_label"] = self.operation_label(item["operation_type"])
        item["is_configured"] = True
        steps: list[dict] = []
        for step in workflow.get("steps") or []:
            approvers: list[dict] = []
            for user_id in step.get("approver_user_ids") or []:
                user = self._user_store.get_by_user_id(user_id)
                approvers.append(
                    {
                        "user_id": user_id,
                        "username": getattr(user, "username", None) if user else None,
                        "full_name": getattr(user, "full_name", None) if user else None,
                    }
                )
            steps.append(
                {
                    "workflow_step_id": step.get("workflow_step_id"),
                    "step_no": int(step["step_no"]),
                    "step_name": step["step_name"],
                    "approver_user_ids": list(step.get("approver_user_ids") or []),
                    "approvers": approvers,
                }
            )
        item["steps"] = steps
        return item

    def _snapshot_steps(self, workflow_steps: list[dict]) -> list[dict]:
        steps: list[dict] = []
        for item in workflow_steps or []:
            approvers: list[dict] = []
            for user_id in item.get("approver_user_ids") or []:
                user = self._resolve_user(user_id)
                approvers.append(
                    {
                        "user_id": str(user.user_id),
                        "username": str(user.username),
                        "full_name": getattr(user, "full_name", None),
                        "email": getattr(user, "email", None),
                    }
                )
            steps.append(
                {
                    "step_no": int(item["step_no"]),
                    "step_name": str(item["step_name"]),
                    "approvers": approvers,
                }
            )
        return steps

    def upsert_workflow(self, *, operation_type: str, name: str | None, steps: list[dict]) -> dict:
        clean_type = self._require_supported_operation_type(operation_type)
        normalized_steps = self._build_workflow_steps(steps=steps)
        workflow_name = str(name or "").strip() or f"{self.operation_label(clean_type)}审批流"
        stored = self._store.upsert_workflow(
            operation_type=clean_type,
            name=workflow_name,
            steps=normalized_steps,
        )
        return self._enrich_workflow(stored)

    def list_workflows(self) -> list[dict]:
        configured = {item["operation_type"]: item for item in self._store.list_workflows()}
        items: list[dict] = []
        for operation_type in SUPPORTED_OPERATION_TYPES:
            workflow = configured.get(operation_type)
            if workflow:
                items.append(self._enrich_workflow(workflow))
            else:
                items.append(
                    {
                        "operation_type": operation_type,
                        "operation_label": self.operation_label(operation_type),
                        "name": f"{self.operation_label(operation_type)}审批流",
                        "is_configured": False,
                        "is_active": False,
                        "steps": [],
                    }
                )
        return items

    def get_workflow(self, *, operation_type: str) -> dict:
        clean_type = self._require_supported_operation_type(operation_type)
        workflow = self._store.get_workflow(clean_type)
        if not workflow:
            raise OperationApprovalServiceError("operation_workflow_not_configured", status_code=404)
        return self._enrich_workflow(workflow)

    def _to_brief(self, item: dict) -> dict:
        return {
            "request_id": item["request_id"],
            "operation_type": item["operation_type"],
            "operation_label": self.operation_label(item["operation_type"]),
            "status": item["status"],
            "current_step_no": item.get("current_step_no"),
            "current_step_name": item.get("current_step_name"),
            "submitted_at_ms": item["submitted_at_ms"],
            "target_ref": item.get("target_ref"),
            "target_label": item.get("target_label"),
            "applicant_user_id": item.get("applicant_user_id"),
            "applicant_username": item.get("applicant_username"),
            "summary": item.get("summary") or {},
            "last_error": item.get("last_error"),
        }

    def _require_request_detail(self, request_id: str) -> dict:
        data = self._store.get_request(request_id)
        if not data:
            raise OperationApprovalServiceError("operation_request_not_found", status_code=404)
        return data

    async def create_request(self, *, operation_type: str, ctx: Any, **kwargs) -> dict:
        clean_type = self._require_supported_operation_type(operation_type)
        workflow = self._store.get_workflow(clean_type)
        if not workflow or not (workflow.get("steps") or []):
            raise OperationApprovalServiceError("operation_workflow_not_configured", status_code=400)
        handler = HANDLER_REGISTRY.get(clean_type)
        if handler is None:
            raise OperationApprovalServiceError("operation_handler_not_configured", status_code=500)
        request_id = str(uuid4())
        prepared = await handler.prepare_request(request_id=request_id, ctx=ctx, **kwargs)
        snapshot_steps = self._snapshot_steps(workflow["steps"])
        created = self._store.create_request(
            request_id=request_id,
            operation_type=clean_type,
            workflow_name=str(workflow["name"]),
            applicant_user_id=str(ctx.user.user_id),
            applicant_username=str(ctx.user.username),
            company_id=(int(ctx.user.company_id) if getattr(ctx.user, "company_id", None) is not None else None),
            department_id=(
                int(ctx.user.department_id) if getattr(ctx.user, "department_id", None) is not None else None
            ),
            target_ref=prepared.target_ref,
            target_label=prepared.target_label,
            summary=prepared.summary,
            payload=prepared.payload,
            workflow_snapshot={"name": workflow["name"], "steps": snapshot_steps},
            steps=snapshot_steps,
            artifacts=[
                {
                    "artifact_type": artifact.artifact_type,
                    "file_path": artifact.file_path,
                    "file_name": artifact.file_name,
                    "mime_type": artifact.mime_type,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                    "meta": artifact.meta,
                }
                for artifact in prepared.artifacts
            ],
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_submitted",
            actor_user_id=str(ctx.user.user_id),
            actor_username=str(ctx.user.username),
            step_no=int(created["current_step_no"] or 0) if created.get("current_step_no") is not None else None,
            payload={"operation_type": clean_type, "target_ref": prepared.target_ref, "target_label": prepared.target_label},
        )
        if created.get("current_step_no") is not None:
            self._store.add_event(
                request_id=request_id,
                event_type="step_activated",
                actor_user_id=str(ctx.user.user_id),
                actor_username=str(ctx.user.username),
                step_no=int(created["current_step_no"]),
                payload={"current_step_name": created.get("current_step_name")},
            )
        self._audit_submit(ctx=ctx, created=created)
        self._notify_submission(created)
        return self._to_brief(self._store.get_request(request_id))

    def list_requests_for_user(self, *, requester_user: Any, view: str, limit: int = 100) -> dict:
        clean_view = str(view or "mine").strip().lower()
        is_admin = bool(str(getattr(requester_user, "role", "") or "") == "admin")
        if clean_view == "mine":
            items = self._store.list_requests(applicant_user_id=str(requester_user.user_id), limit=limit)
        elif clean_view == "todo":
            items = self._store.list_requests(pending_approver_user_id=str(requester_user.user_id), limit=limit)
        elif clean_view == "all":
            if not is_admin:
                raise OperationApprovalServiceError("admin_required", status_code=403)
            items = self._store.list_requests(include_all=True, limit=limit)
        else:
            raise OperationApprovalServiceError("operation_request_view_invalid", status_code=400)
        return {"items": [self._to_brief(item) for item in items], "count": len(items)}

    def list_todos_for_user(self, *, requester_user: Any, limit: int = 100) -> dict:
        items = self._store.list_requests(pending_approver_user_id=str(requester_user.user_id), limit=limit)
        return {"items": [self._to_brief(item) for item in items], "count": len(items)}

    def get_request_detail_for_user(self, *, request_id: str, requester_user_id: str, is_admin: bool) -> dict:
        request_data = self._require_request_detail(request_id)
        if not is_admin:
            approver_request_ids = set(self._store.list_request_ids_for_user(user_id=requester_user_id))
            if request_data["applicant_user_id"] != requester_user_id and request_id not in approver_request_ids:
                raise OperationApprovalServiceError("operation_request_not_visible", status_code=403)
        data = dict(request_data)
        data["operation_label"] = self.operation_label(data["operation_type"])
        return data

    def _find_next_step(self, request_data: dict, *, current_step_no: int) -> dict | None:
        for step in request_data.get("steps") or []:
            if int(step["step_no"]) == int(current_step_no) + 1:
                return step
        return None

    def _build_signature_payload(self, *, request_data: dict, action: str, step_no: int, before_status: str, after_status: str):
        return {
            "request_id": request_data["request_id"],
            "operation_type": request_data["operation_type"],
            "operation_label": self.operation_label(request_data["operation_type"]),
            "action": action,
            "step_no": step_no,
            "before_status": before_status,
            "after_status": after_status,
            "target_ref": request_data.get("target_ref"),
            "target_label": request_data.get("target_label"),
        }

    def _require_signature_service(self):
        if self._signature_service is None:
            raise OperationApprovalServiceError("electronic_signature_service_unavailable", status_code=500)
        return self._signature_service

    def approve_request(
        self,
        *,
        request_id: str,
        actor_user: Any,
        sign_token: str,
        signature_meaning: str,
        signature_reason: str,
        notes: str | None,
    ) -> dict:
        request_data = self._require_request_detail(request_id)
        if request_data["status"] != REQUEST_STATUS_IN_APPROVAL:
            raise OperationApprovalServiceError("operation_request_not_active", status_code=409)
        active_step = self._store.get_active_step(request_id=request_id)
        if not active_step:
            raise OperationApprovalServiceError("operation_request_active_step_missing", status_code=409)
        approver = self._store.get_step_approver(
            request_id=request_id,
            step_no=int(active_step["step_no"]),
            approver_user_id=str(actor_user.user_id),
        )
        if not approver:
            raise OperationApprovalServiceError("operation_request_not_current_approver", status_code=403)
        if approver["status"] != APPROVER_STATUS_PENDING:
            raise OperationApprovalServiceError("operation_request_approver_already_acted", status_code=409)

        signature_service = self._require_signature_service()
        try:
            signing_context = signature_service.consume_sign_token(
                user=actor_user,
                sign_token=sign_token,
                action="operation_approval_approve",
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

        remaining_after_this = self._store.count_pending_approvers(request_step_id=active_step["request_step_id"]) - 1
        next_step = self._find_next_step(request_data, current_step_no=int(active_step["step_no"]))
        after_status = (
            REQUEST_STATUS_IN_APPROVAL
            if remaining_after_this > 0 or next_step is not None
            else REQUEST_STATUS_APPROVED_PENDING_EXECUTION
        )
        try:
            signature = signature_service.create_signature(
                signing_context=signing_context,
                user=actor_user,
                record_type="operation_approval_request",
                record_id=str(request_id),
                action="operation_approval_approve",
                meaning=signature_meaning,
                reason=signature_reason,
                record_payload=self._build_signature_payload(
                    request_data=request_data,
                    action="approve",
                    step_no=int(active_step["step_no"]),
                    before_status=request_data["status"],
                    after_status=after_status,
                ),
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

        self._store.mark_step_approver_action(
            request_id=request_id,
            step_no=int(active_step["step_no"]),
            approver_user_id=str(actor_user.user_id),
            approver_username=str(actor_user.username),
            status=APPROVER_STATUS_APPROVED,
            action="approve",
            notes=notes,
            signature_id=str(signature.signature_id),
        )
        self._store.add_event(
            request_id=request_id,
            event_type="step_approved_by_user",
            actor_user_id=str(actor_user.user_id),
            actor_username=str(actor_user.username),
            step_no=int(active_step["step_no"]),
            payload={"notes": notes, "signature_id": signature.signature_id},
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data,
            action="operation_approval_approve",
            reason=signature_reason,
            signature_id=str(signature.signature_id),
            step_no=int(active_step["step_no"]),
            meta={"signature_meaning": signature_meaning},
        )

        if remaining_after_this > 0:
            return self.get_request_detail_for_user(
                request_id=request_id,
                requester_user_id=str(actor_user.user_id),
                is_admin=bool(getattr(actor_user, "role", "") == "admin"),
            )

        self._store.set_step_status(request_step_id=active_step["request_step_id"], status=STEP_STATUS_APPROVED, completed=True)
        if next_step is None:
            self._store.set_request_status(
                request_id=request_id,
                status=REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
                current_step_no=int(active_step["step_no"]),
                current_step_name=str(active_step["step_name"]),
            )
            self._store.add_event(
                request_id=request_id,
                event_type="request_approved",
                actor_user_id=str(actor_user.user_id),
                actor_username=str(actor_user.username),
                step_no=int(active_step["step_no"]),
                payload={"signature_id": signature.signature_id},
            )
            self._execute_request(request_id=request_id)
        else:
            self._activate_next_step(
                request_id=request_id,
                step_no=int(next_step["step_no"]),
                step_name=str(next_step["step_name"]),
                actor_user_id=str(actor_user.user_id),
                actor_username=str(actor_user.username),
            )
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user_id=str(actor_user.user_id),
            is_admin=bool(getattr(actor_user, "role", "") == "admin"),
        )

    def reject_request(
        self,
        *,
        request_id: str,
        actor_user: Any,
        sign_token: str,
        signature_meaning: str,
        signature_reason: str,
        notes: str | None,
    ) -> dict:
        request_data = self._require_request_detail(request_id)
        if request_data["status"] != REQUEST_STATUS_IN_APPROVAL:
            raise OperationApprovalServiceError("operation_request_not_active", status_code=409)
        active_step = self._store.get_active_step(request_id=request_id)
        if not active_step:
            raise OperationApprovalServiceError("operation_request_active_step_missing", status_code=409)
        approver = self._store.get_step_approver(
            request_id=request_id,
            step_no=int(active_step["step_no"]),
            approver_user_id=str(actor_user.user_id),
        )
        if not approver:
            raise OperationApprovalServiceError("operation_request_not_current_approver", status_code=403)
        if approver["status"] != APPROVER_STATUS_PENDING:
            raise OperationApprovalServiceError("operation_request_approver_already_acted", status_code=409)

        signature_service = self._require_signature_service()
        try:
            signing_context = signature_service.consume_sign_token(
                user=actor_user,
                sign_token=sign_token,
                action="operation_approval_reject",
            )
            signature = signature_service.create_signature(
                signing_context=signing_context,
                user=actor_user,
                record_type="operation_approval_request",
                record_id=str(request_id),
                action="operation_approval_reject",
                meaning=signature_meaning,
                reason=signature_reason,
                record_payload=self._build_signature_payload(
                    request_data=request_data,
                    action="reject",
                    step_no=int(active_step["step_no"]),
                    before_status=request_data["status"],
                    after_status=REQUEST_STATUS_REJECTED,
                ),
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

        self._store.mark_step_approver_action(
            request_id=request_id,
            step_no=int(active_step["step_no"]),
            approver_user_id=str(actor_user.user_id),
            approver_username=str(actor_user.username),
            status=APPROVER_STATUS_REJECTED,
            action="reject",
            notes=notes,
            signature_id=str(signature.signature_id),
        )
        self._store.set_step_status(request_step_id=active_step["request_step_id"], status=STEP_STATUS_REJECTED, completed=True)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_REJECTED,
            current_step_no=int(active_step["step_no"]),
            current_step_name=str(active_step["step_name"]),
            completed=True,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_rejected",
            actor_user_id=str(actor_user.user_id),
            actor_username=str(actor_user.username),
            step_no=int(active_step["step_no"]),
            payload={"notes": notes, "signature_id": signature.signature_id},
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data,
            action="operation_approval_reject",
            reason=signature_reason,
            signature_id=str(signature.signature_id),
            step_no=int(active_step["step_no"]),
            meta={"signature_meaning": signature_meaning},
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(self._store.get_request(request_id))
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user_id=str(actor_user.user_id),
            is_admin=bool(getattr(actor_user, "role", "") == "admin"),
        )

    def withdraw_request(self, *, request_id: str, actor_user: Any, reason: str | None) -> dict:
        request_data = self._require_request_detail(request_id)
        is_admin = bool(str(getattr(actor_user, "role", "") or "") == "admin")
        if request_data["status"] != REQUEST_STATUS_IN_APPROVAL:
            raise OperationApprovalServiceError("operation_request_not_withdrawable", status_code=409)
        if not is_admin and request_data["applicant_user_id"] != str(actor_user.user_id):
            raise OperationApprovalServiceError("operation_request_withdraw_forbidden", status_code=403)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_WITHDRAWN,
            current_step_no=request_data.get("current_step_no"),
            current_step_name=request_data.get("current_step_name"),
            completed=True,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_withdrawn",
            actor_user_id=str(actor_user.user_id),
            actor_username=str(actor_user.username),
            step_no=request_data.get("current_step_no"),
            payload={"reason": reason},
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data,
            action="operation_approval_withdraw",
            reason=reason,
            signature_id=None,
            step_no=request_data.get("current_step_no"),
            meta={},
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(self._store.get_request(request_id))
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user_id=str(actor_user.user_id),
            is_admin=is_admin,
        )

    def _activate_next_step(
        self,
        *,
        request_id: str,
        step_no: int,
        step_name: str,
        actor_user_id: str,
        actor_username: str,
    ) -> None:
        request_data = self._store.get_request(request_id)
        target_step = None
        for step in request_data.get("steps") or []:
            if int(step["step_no"]) == int(step_no):
                target_step = step
                break
        if not target_step:
            raise OperationApprovalServiceError("operation_request_next_step_missing", status_code=409)
        self._store.set_step_status(request_step_id=target_step["request_step_id"], status=STEP_STATUS_ACTIVE, activated=True)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_IN_APPROVAL,
            current_step_no=int(step_no),
            current_step_name=str(step_name),
        )
        self._store.add_event(
            request_id=request_id,
            event_type="step_activated",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=int(step_no),
            payload={"current_step_name": step_name},
        )
        self._notify_step_started(self._store.get_request(request_id))

    def _execute_request(self, *, request_id: str) -> None:
        request_data = self._require_request_detail(request_id)
        handler = HANDLER_REGISTRY.get(str(request_data["operation_type"]))
        if handler is None:
            raise OperationApprovalServiceError("operation_handler_not_configured", status_code=500)
        applicant_user = self._get_user(str(request_data["applicant_user_id"]))
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_EXECUTING,
            current_step_no=request_data.get("current_step_no"),
            current_step_name=request_data.get("current_step_name"),
            execution_started=True,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="execution_started",
            actor_user_id=str(applicant_user.user_id),
            actor_username=str(applicant_user.username),
            step_no=request_data.get("current_step_no"),
            payload={},
        )
        self._audit_execute(request_data=request_data, applicant_user=applicant_user, action="operation_approval_execute_start", meta={})
        try:
            result = handler.execute_request(
                request_data=self._store.get_request(request_id),
                deps=self._deps,
                applicant_user=applicant_user,
            )
        except Exception as exc:
            code = str(exc) or exc.__class__.__name__
            self._store.set_request_status(
                request_id=request_id,
                status=REQUEST_STATUS_EXECUTION_FAILED,
                current_step_no=request_data.get("current_step_no"),
                current_step_name=request_data.get("current_step_name"),
                completed=True,
                last_error=code,
                result_payload={"error": code},
            )
            self._store.add_event(
                request_id=request_id,
                event_type="execution_failed",
                actor_user_id=str(applicant_user.user_id),
                actor_username=str(applicant_user.username),
                step_no=request_data.get("current_step_no"),
                payload={"error": code},
            )
            self._audit_execute(
                request_data=request_data,
                applicant_user=applicant_user,
                action="operation_approval_execute_failed",
                meta={"error": code},
            )
            self._cleanup_artifacts(request_id=request_id)
            self._notify_final(self._store.get_request(request_id))
            return
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_EXECUTED,
            current_step_no=request_data.get("current_step_no"),
            current_step_name=request_data.get("current_step_name"),
            completed=True,
            executed=True,
            result_payload=result,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="execution_completed",
            actor_user_id=str(applicant_user.user_id),
            actor_username=str(applicant_user.username),
            step_no=request_data.get("current_step_no"),
            payload=result,
        )
        self._audit_execute(
            request_data=request_data,
            applicant_user=applicant_user,
            action="operation_approval_execute_success",
            meta=result,
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(self._store.get_request(request_id))

    def _audit_submit(self, *, ctx: Any, created: dict) -> None:
        if not self._deps or getattr(self._deps, "audit_log_store", None) is None:
            return
        self._deps.audit_log_store.log_event(
            action="operation_approval_submit",
            actor=ctx.payload.sub,
            source="operation_approval",
            resource_type="operation_approval_request",
            resource_id=created["request_id"],
            request_id=created["request_id"],
            event_type="create",
            after=self._to_brief(created),
            meta={"operation_type": created["operation_type"]},
            **actor_fields_from_ctx(self._deps, ctx),
        )

    def _recipients_for_step(self, request_data: dict) -> list[dict]:
        current_step_no = request_data.get("current_step_no")
        if current_step_no is None:
            return []
        for step in request_data.get("steps") or []:
            if int(step["step_no"]) != int(current_step_no):
                continue
            return [
                {
                    "user_id": approver["approver_user_id"],
                    "username": approver.get("approver_username"),
                    "email": getattr(self._user_store.get_by_user_id(approver["approver_user_id"]), "email", None),
                }
                for approver in step.get("approvers") or []
                if approver.get("status") == APPROVER_STATUS_PENDING
            ]
        return []

    def _applicant_recipient(self, request_data: dict) -> list[dict]:
        user = self._user_store.get_by_user_id(str(request_data["applicant_user_id"]))
        if not user:
            return []
        return [{"user_id": str(user.user_id), "username": str(user.username), "email": getattr(user, "email", None)}]

    def _notify_submission(self, request_data: dict) -> None:
        recipients = self._applicant_recipient(request_data)
        self._notify_inbox(
            recipients=recipients,
            title=f"{self.operation_label(request_data['operation_type'])}申请已提交",
            body=f"申请单 {request_data['request_id']} 已创建，当前状态：{request_data['status']}",
            event_type="operation_approval_submitted",
            request_data=request_data,
        )
        self._notify_external(
            recipients=recipients,
            event_type="operation_approval_submitted",
            request_data=request_data,
        )
        self._notify_step_started(request_data)

    def _notify_step_started(self, request_data: dict) -> None:
        recipients = self._recipients_for_step(request_data)
        if not recipients:
            return
        self._notify_inbox(
            recipients=recipients,
            title=f"{self.operation_label(request_data['operation_type'])}待审批",
            body=f"申请单 {request_data['request_id']} 已到第 {request_data.get('current_step_no')} 层：{request_data.get('current_step_name')}",
            event_type="operation_approval_todo",
            request_data=request_data,
        )
        self._notify_external(recipients=recipients, event_type="operation_approval_todo", request_data=request_data)

    def _notify_final(self, request_data: dict) -> None:
        status = str(request_data["status"])
        event_type = {
            REQUEST_STATUS_REJECTED: "operation_approval_rejected",
            REQUEST_STATUS_WITHDRAWN: "operation_approval_withdrawn",
            REQUEST_STATUS_EXECUTED: "operation_approval_executed",
            REQUEST_STATUS_EXECUTION_FAILED: "operation_approval_execution_failed",
        }.get(status)
        if not event_type:
            return
        recipients = self._applicant_recipient(request_data)
        self._notify_inbox(
            recipients=recipients,
            title=f"{self.operation_label(request_data['operation_type'])}申请结果更新",
            body=f"申请单 {request_data['request_id']} 当前状态：{status}",
            event_type=event_type,
            request_data=request_data,
        )
        self._notify_external(recipients=recipients, event_type=event_type, request_data=request_data)

    def _notify_inbox(self, *, recipients: list[dict], title: str, body: str, event_type: str, request_data: dict) -> None:
        if self._inbox_service is None or not recipients:
            return
        self._inbox_service.notify_users(
            recipients=recipients,
            title=title,
            body=body,
            event_type=event_type,
            link_path=f"/approvals?request_id={request_data['request_id']}",
            payload={"request_id": request_data["request_id"], "operation_type": request_data["operation_type"], "status": request_data["status"]},
        )
        self._store.add_event(
            request_id=request_data["request_id"],
            event_type="notification_inbox_created",
            actor_user_id=None,
            actor_username=None,
            step_no=request_data.get("current_step_no"),
            payload={"event_type": event_type, "recipient_count": len(recipients)},
        )

    def _notify_external(self, *, recipients: list[dict], event_type: str, request_data: dict) -> None:
        if self._notification_service is None or not recipients:
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_external_skipped",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "reason": "notification_service_unavailable"},
            )
            return
        try:
            self._notification_service.notify_event(
                event_type=event_type,
                payload={
                    "request_id": request_data["request_id"],
                    "operation_type": request_data["operation_type"],
                    "status": request_data["status"],
                    "target_ref": request_data.get("target_ref"),
                    "target_label": request_data.get("target_label"),
                    "current_step_no": request_data.get("current_step_no"),
                    "current_step_name": request_data.get("current_step_name"),
                },
                recipients=recipients,
                dedupe_key=(
                    f"{event_type}:{request_data['request_id']}:"
                    f"{request_data.get('current_step_no') or 0}:{request_data.get('status')}"
                ),
            )
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_external_enqueued",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "recipient_count": len(recipients)},
            )
        except Exception as exc:
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_external_failed",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "error": str(exc)},
            )

    def _cleanup_artifacts(self, *, request_id: str) -> None:
        request_data = self._store.get_request(request_id)
        for artifact in request_data.get("artifacts") or []:
            artifact_id = str(artifact["artifact_id"])
            file_path = str(artifact.get("file_path") or "")
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                parent = os.path.dirname(file_path)
                while parent and os.path.isdir(parent):
                    try:
                        if os.listdir(parent):
                            break
                        os.rmdir(parent)
                    except OSError:
                        break
                    parent = os.path.dirname(parent)
                self._store.mark_artifact_cleanup(artifact_id=artifact_id, cleanup_status="cleaned")
            except Exception as exc:
                self._store.mark_artifact_cleanup(artifact_id=artifact_id, cleanup_status="cleanup_failed")
                self._store.add_event(
                    request_id=request_id,
                    event_type="approval_artifact_cleanup_failed",
                    actor_user_id=None,
                    actor_username=None,
                    step_no=request_data.get("current_step_no"),
                    payload={"artifact_id": artifact_id, "error": str(exc)},
                )

    def _audit_action(
        self,
        *,
        actor_user: Any,
        request_data: dict,
        action: str,
        reason: str | None,
        signature_id: str | None,
        step_no: int | None,
        meta: dict,
    ) -> None:
        if not self._deps or getattr(self._deps, "audit_log_store", None) is None:
            return
        self._deps.audit_log_store.log_event(
            action=action,
            actor=str(actor_user.user_id),
            source="operation_approval",
            resource_type="operation_approval_request",
            resource_id=request_data["request_id"],
            request_id=request_data["request_id"],
            event_type="update",
            reason=reason,
            signature_id=signature_id,
            meta={"operation_type": request_data["operation_type"], "step_no": step_no, **(meta or {})},
            **actor_fields_from_user(self._deps, actor_user),
        )

    def _audit_execute(self, *, request_data: dict, applicant_user: Any, action: str, meta: dict) -> None:
        if not self._deps or getattr(self._deps, "audit_log_store", None) is None:
            return
        self._deps.audit_log_store.log_event(
            action=action,
            actor=str(applicant_user.user_id),
            source="operation_approval",
            resource_type="operation_approval_request",
            resource_id=request_data["request_id"],
            request_id=request_data["request_id"],
            event_type="update",
            meta={"operation_type": request_data["operation_type"], **(meta or {})},
            **actor_fields_from_user(self._deps, applicant_user),
        )
