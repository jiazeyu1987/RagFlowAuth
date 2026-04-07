from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from backend.services.electronic_signature import ElectronicSignatureError

from .audit_service import OperationApprovalAuditService
from .decision_service import OperationApprovalDecisionService
from .execution_service import OperationApprovalExecutionService
from .handlers import HANDLER_REGISTRY
from .migration_service import OperationApprovalMigrationService
from .notification_service import OperationApprovalNotificationService
from .store import OperationApprovalStore
from .types import (
    APPROVAL_RULE_ALL,
    OPERATION_TYPE_LABELS,
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    SPECIAL_ROLE_DIRECT_MANAGER,
    SPECIAL_ROLE_LABELS,
    SUPPORTED_REQUEST_STATUSES,
    SUPPORTED_SPECIAL_ROLES,
    SUPPORTED_WORKFLOW_MEMBER_TYPES,
    SUPPORTED_OPERATION_TYPES,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
    WORKFLOW_MEMBER_TYPE_USER,
    ApprovalRequestEventRecord,
    ApprovalRequestRecord,
    ApprovalRequestStepRecord,
    ApprovalWorkflowMemberRecord,
    ApprovalWorkflowRecord,
    ApprovalWorkflowStepRecord,
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
        execution_deps_resolver: Callable[[int | str], Any] | None = None,
    ):
        self._store = store
        self._user_store = user_store
        self._inbox_service = inbox_service
        self._notification_service = notification_service
        self._signature_service = electronic_signature_service
        self._deps = deps
        self._execution_deps_resolver = execution_deps_resolver
        self._decision_service = OperationApprovalDecisionService(
            store=store,
            error_factory=lambda code, status_code=400: OperationApprovalServiceError(code, status_code=status_code),
        )
        self._audit_service = OperationApprovalAuditService(deps=deps, brief_resolver=self._to_brief)
        self._notification_coordinator = OperationApprovalNotificationService(
            store=store,
            user_store=user_store,
            notification_service=notification_service,
            operation_label_resolver=self.operation_label,
        )
        self._execution_service = OperationApprovalExecutionService(
            store=store,
            handler_registry=HANDLER_REGISTRY,
            get_user=self._get_user,
            resolve_execution_deps=lambda request_data: self._resolve_execution_deps(request_data=request_data),
            audit_execute=self._audit_execute,
            cleanup_artifacts=lambda *, request_id: self._cleanup_artifacts(request_id=request_id),
            notify_final=self._notify_final,
            transition_request_to_executing_state=self._decision_service.transition_request_to_executing_state,
            finalize_request_execution_state=self._decision_service.finalize_request_execution_state,
            error_factory=lambda code, status_code=400: OperationApprovalServiceError(code, status_code=status_code),
        )
        self._migration_service = OperationApprovalMigrationService(
            store=store,
            user_store=user_store,
            deps=deps,
            get_user=self._get_user,
            resolve_user=self._resolve_user,
            get_user_by_username=self._get_user_by_username,
            normalize_company_id=self._normalize_company_id,
            error_factory=lambda code, status_code=400: OperationApprovalServiceError(code, status_code=status_code),
            error_type=OperationApprovalServiceError,
        )

    @staticmethod
    def operation_label(operation_type: str) -> str:
        return OPERATION_TYPE_LABELS.get(operation_type, operation_type)

    def _require_supported_operation_type(self, operation_type: str) -> str:
        value = str(operation_type or "").strip()
        if value not in SUPPORTED_OPERATION_TYPES:
            raise OperationApprovalServiceError("operation_type_unsupported", status_code=400)
        return value

    def _normalize_request_status_filter(self, status: str | None) -> str | None:
        value = str(status or "").strip().lower()
        if not value or value == "all":
            return None
        if value not in SUPPORTED_REQUEST_STATUSES:
            raise OperationApprovalServiceError("operation_request_status_invalid", status_code=400)
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

    @staticmethod
    def _is_admin(user: Any) -> bool:
        return bool(str(getattr(user, "role", "") or "").strip().lower() == "admin")

    @staticmethod
    def _normalize_company_id(value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    def _get_user_by_username(self, username: str):
        getter = getattr(self._user_store, "get_by_username", None)
        if not callable(getter):
            return None
        return getter(username)

    @staticmethod
    def _to_request_record(request_data: dict | ApprovalRequestRecord) -> ApprovalRequestRecord:
        if isinstance(request_data, ApprovalRequestRecord):
            return request_data
        return ApprovalRequestRecord.from_dict(request_data)

    @staticmethod
    def _to_workflow_record(workflow_data: dict | ApprovalWorkflowRecord) -> ApprovalWorkflowRecord:
        if isinstance(workflow_data, ApprovalWorkflowRecord):
            return workflow_data
        return ApprovalWorkflowRecord.from_dict(workflow_data)

    def _request_visible_to_user(self, *, request_data: dict | ApprovalRequestRecord, requester_user: Any) -> bool:
        request_record = self._to_request_record(request_data)
        requester_user_id = str(getattr(requester_user, "user_id", "") or "").strip()
        if not requester_user_id:
            return False
        if self._is_admin(requester_user):
            requester_company_id = self._normalize_company_id(getattr(requester_user, "company_id", None))
            request_company_id = self._normalize_company_id(request_record.company_id)
            if requester_company_id is None:
                return True
            return request_company_id == requester_company_id
        approver_request_ids = set(self._store.list_request_ids_for_user(user_id=requester_user_id))
        return (
            request_record.applicant_user_id == requester_user_id
            or request_record.request_id in approver_request_ids
        )

    def _build_workflow_steps(self, *, steps: list[dict]) -> list[dict]:
        if not steps:
            raise OperationApprovalServiceError("workflow_steps_required", status_code=400)
        normalized: list[dict] = []
        for index, item in enumerate(steps, start=1):
            step_name = str((item or {}).get("step_name") or "").strip()
            if not step_name:
                raise OperationApprovalServiceError("workflow_step_name_required", status_code=400)
            raw_members = (item or {}).get("members")
            if raw_members is None and (item or {}).get("approver_user_ids") is not None:
                raw_members = [
                    {"member_type": WORKFLOW_MEMBER_TYPE_USER, "member_ref": raw_user_id}
                    for raw_user_id in ((item or {}).get("approver_user_ids") or [])
                ]
            if not isinstance(raw_members, list):
                raise OperationApprovalServiceError("workflow_step_members_required", status_code=400)
            members: list[dict] = []
            for raw_member in raw_members:
                if not isinstance(raw_member, dict):
                    raise OperationApprovalServiceError("workflow_step_member_invalid", status_code=400)
                member_type = str(raw_member.get("member_type") or "").strip()
                member_ref = str(raw_member.get("member_ref") or "").strip()
                if member_type not in SUPPORTED_WORKFLOW_MEMBER_TYPES:
                    raise OperationApprovalServiceError("workflow_step_member_type_invalid", status_code=400)
                if not member_ref:
                    raise OperationApprovalServiceError("workflow_step_member_ref_required", status_code=400)
                if member_type == WORKFLOW_MEMBER_TYPE_USER:
                    self._resolve_user(member_ref)
                else:
                    if member_ref not in SUPPORTED_SPECIAL_ROLES:
                        raise OperationApprovalServiceError("workflow_step_special_role_invalid", status_code=400)
                members.append({"member_type": member_type, "member_ref": member_ref})
            if not members:
                raise OperationApprovalServiceError("workflow_step_members_required", status_code=400)
            normalized.append({"step_no": index, "step_name": step_name, "members": members})
        return normalized

    def _workflow_member_view(self, member: dict) -> dict:
        member_record = ApprovalWorkflowMemberRecord.from_dict(member)
        member_type = member_record.member_type
        member_ref = member_record.member_ref
        if member_type == WORKFLOW_MEMBER_TYPE_USER:
            user = self._user_store.get_by_user_id(member_ref)
            return {
                "member_type": member_type,
                "member_ref": member_ref,
                "user_id": member_ref,
                "username": getattr(user, "username", None) if user else None,
                "full_name": getattr(user, "full_name", None) if user else None,
                "label": getattr(user, "full_name", None) or getattr(user, "username", None) or member_ref,
            }
        return {
            "member_type": member_type,
            "member_ref": member_ref,
            "label": SPECIAL_ROLE_LABELS.get(member_ref, member_ref),
        }

    def _enrich_workflow(self, workflow: dict) -> dict:
        workflow_record = self._to_workflow_record(workflow)
        item = workflow_record.to_dict()
        item["operation_label"] = self.operation_label(workflow_record.operation_type)
        item["is_configured"] = True
        steps: list[dict] = []
        for step in workflow_record.steps:
            steps.append(
                {
                    "workflow_step_id": step.workflow_step_id,
                    "step_no": step.step_no,
                    "step_name": step.step_name,
                    "members": [self._workflow_member_view(member.to_dict()) for member in step.members],
                }
            )
        item["steps"] = steps
        return item

    def _resolve_user_full_name(self, user_id: str | None, user_cache: dict[str, Any] | None = None) -> str | None:
        clean_user_id = str(user_id or "").strip()
        if not clean_user_id:
            return None
        cache = user_cache if user_cache is not None else {}
        if clean_user_id not in cache:
            cache[clean_user_id] = self._user_store.get_by_user_id(clean_user_id)
        user = cache[clean_user_id]
        full_name = getattr(user, "full_name", None) if user is not None else None
        normalized = str(full_name or "").strip()
        return normalized or None

    def _enrich_request_steps(self, steps: list[dict] | list[ApprovalRequestStepRecord]) -> list[dict]:
        user_cache: dict[str, Any] = {}

        enriched_steps: list[dict] = []
        for step in steps or []:
            step_record = step if isinstance(step, ApprovalRequestStepRecord) else ApprovalRequestStepRecord.from_dict(step)
            next_step = step_record.to_dict()
            next_step["approvers"] = []
            for approver in step_record.approvers:
                next_approver = approver.to_dict()
                next_approver["approver_full_name"] = self._resolve_user_full_name(
                    approver.approver_user_id,
                    user_cache,
                )
                next_step["approvers"].append(next_approver)
            enriched_steps.append(next_step)
        return enriched_steps

    def _enrich_request_events(self, events: list[dict] | list[ApprovalRequestEventRecord]) -> list[dict]:
        user_cache: dict[str, Any] = {}

        enriched_events: list[dict] = []
        for event in events or []:
            event_record = event if isinstance(event, ApprovalRequestEventRecord) else ApprovalRequestEventRecord.from_dict(event)
            next_event = event_record.to_dict()
            next_event["actor_full_name"] = self._resolve_user_full_name(event_record.actor_user_id, user_cache)
            enriched_events.append(next_event)
        return enriched_events

    def _snapshot_workflow_steps(self, workflow_steps: list[dict]) -> list[dict]:
        steps: list[dict] = []
        for item in workflow_steps or []:
            step_record = item if isinstance(item, ApprovalWorkflowStepRecord) else ApprovalWorkflowStepRecord.from_dict(item)
            steps.append(
                {
                    "step_no": step_record.step_no,
                    "step_name": step_record.step_name,
                    "approval_rule": step_record.approval_rule,
                    "members": [member.to_dict() for member in step_record.members],
                }
            )
        return steps

    def _resolve_direct_manager(self, applicant_user: Any) -> tuple[Any | None, str | None]:
        manager_user_id = str(getattr(applicant_user, "manager_user_id", "") or "").strip()
        if not manager_user_id:
            return None, "direct_manager_missing"
        user = self._user_store.get_by_user_id(manager_user_id)
        if not user:
            return None, "direct_manager_not_found"
        if str(getattr(user, "status", "") or "").strip().lower() != "active":
            return None, "direct_manager_inactive"
        return user, None

    def _materialize_request_steps(self, *, workflow_steps: list[dict], applicant_user: Any) -> tuple[list[dict], list[dict]]:
        materialized_steps: list[dict] = []
        events: list[dict] = []
        for item in workflow_steps or []:
            step_record = item if isinstance(item, ApprovalWorkflowStepRecord) else ApprovalWorkflowStepRecord.from_dict(item)
            resolved_approvers: dict[str, dict] = {}
            for member in step_record.members:
                member_type = member.member_type
                member_ref = member.member_ref
                if member_type == WORKFLOW_MEMBER_TYPE_USER:
                    user = self._resolve_user(member_ref)
                    resolved_approvers[str(user.user_id)] = {
                        "user_id": str(user.user_id),
                        "username": str(user.username),
                        "full_name": getattr(user, "full_name", None),
                        "email": getattr(user, "email", None),
                    }
                    continue
                if member_type == WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE and member_ref == SPECIAL_ROLE_DIRECT_MANAGER:
                    manager_user, reason = self._resolve_direct_manager(applicant_user)
                    if manager_user is None:
                        events.append(
                            {
                                "event_type": "step_member_auto_skipped",
                                "step_no": step_record.step_no,
                                "payload": {
                                    "step_name": step_record.step_name,
                                    "member_type": member_type,
                                    "member_ref": member_ref,
                                    "reason": reason,
                                },
                            }
                        )
                        continue
                    resolved_approvers[str(manager_user.user_id)] = {
                        "user_id": str(manager_user.user_id),
                        "username": str(manager_user.username),
                        "full_name": getattr(manager_user, "full_name", None),
                        "email": getattr(manager_user, "email", None),
                    }
                    continue
                raise OperationApprovalServiceError("workflow_step_special_role_invalid", status_code=400)
            if resolved_approvers:
                materialized_steps.append(
                    {
                        "step_no": step_record.step_no,
                        "step_name": step_record.step_name,
                        "approval_rule": step_record.approval_rule,
                        "approvers": list(resolved_approvers.values()),
                    }
                )
                continue
            events.append(
                {
                    "event_type": "step_auto_skipped",
                    "step_no": step_record.step_no,
                    "payload": {
                        "step_name": step_record.step_name,
                        "reason": "no_resolved_approvers",
                    },
                }
            )
        return materialized_steps, events

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
        configured = {
            workflow.operation_type: workflow
            for workflow in (self._to_workflow_record(item) for item in self._store.list_workflows())
        }
        items: list[dict] = []
        for operation_type in SUPPORTED_OPERATION_TYPES:
            workflow = configured.get(operation_type)
            if workflow:
                items.append(self._enrich_workflow(workflow.to_dict()))
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

    def _to_brief(self, item: dict | ApprovalRequestRecord) -> dict:
        request_record = self._to_request_record(item)
        return {
            "request_id": request_record.request_id,
            "operation_type": request_record.operation_type,
            "operation_label": self.operation_label(request_record.operation_type),
            "status": request_record.status,
            "current_step_no": request_record.current_step_no,
            "current_step_name": request_record.current_step_name,
            "submitted_at_ms": request_record.submitted_at_ms,
            "target_ref": request_record.target_ref,
            "target_label": request_record.target_label,
            "applicant_user_id": request_record.applicant_user_id,
            "applicant_username": request_record.applicant_username,
            "applicant_full_name": self._resolve_user_full_name(request_record.applicant_user_id),
            "summary": dict(request_record.summary),
            "last_error": request_record.last_error,
        }

    def _require_request_detail(self, request_id: str) -> dict:
        data = self._store.get_request(request_id)
        if not data:
            raise OperationApprovalServiceError("operation_request_not_found", status_code=404)
        return data

    def _require_request_record(self, request_id: str) -> ApprovalRequestRecord:
        return self._to_request_record(self._require_request_detail(request_id))

    async def create_request(self, *, operation_type: str, ctx: Any, **kwargs) -> dict:
        clean_type = self._require_supported_operation_type(operation_type)
        workflow = self._store.get_workflow(clean_type)
        if not workflow or not (workflow.get("steps") or []):
            raise OperationApprovalServiceError("operation_workflow_not_configured", status_code=400)
        workflow_record = self._to_workflow_record(workflow)
        handler = HANDLER_REGISTRY.get(clean_type)
        if handler is None:
            raise OperationApprovalServiceError("operation_handler_not_configured", status_code=500)
        request_id = str(uuid4())
        prepared = await handler.prepare_request(request_id=request_id, ctx=ctx, **kwargs)
        workflow_snapshot_steps = self._snapshot_workflow_steps(workflow_record.steps)
        materialized_steps, materialization_events = self._materialize_request_steps(
            workflow_steps=workflow_record.steps,
            applicant_user=ctx.user,
        )
        created = self._store.create_request(
            request_id=request_id,
            operation_type=clean_type,
            workflow_name=workflow_record.name,
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
            workflow_snapshot={"name": workflow_record.name, "steps": workflow_snapshot_steps},
            steps=materialized_steps,
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
        created_record = self._to_request_record(created)
        self._store.add_event(
            request_id=request_id,
            event_type="request_submitted",
            actor_user_id=str(ctx.user.user_id),
            actor_username=str(ctx.user.username),
            step_no=created_record.current_step_no,
            payload={"operation_type": clean_type, "target_ref": prepared.target_ref, "target_label": prepared.target_label},
        )
        for event in materialization_events:
            self._store.add_event(
                request_id=request_id,
                event_type=str(event["event_type"]),
                actor_user_id=str(ctx.user.user_id),
                actor_username=str(ctx.user.username),
                step_no=event.get("step_no"),
                payload=event.get("payload") or {},
            )
        if created_record.current_step_no is not None:
            self._store.add_event(
                request_id=request_id,
                event_type="step_activated",
                actor_user_id=str(ctx.user.user_id),
                actor_username=str(ctx.user.username),
                step_no=created_record.current_step_no,
                payload={"current_step_name": created_record.current_step_name},
            )
        self._audit_submit(ctx=ctx, created=created)
        current_request = self._require_request_record(request_id)
        self._notify_submission(current_request.to_dict())
        if created_record.current_step_no is None:
            self._store.run_in_transaction(
                lambda conn: self._decision_service.complete_request_approval_state(
                    request_id=request_id,
                    actor_user_id=str(ctx.user.user_id),
                    actor_username=str(ctx.user.username),
                    step_no=None,
                    signature_id=None,
                    auto_approved=True,
                    conn=conn,
                )
            )
            self._execute_request(request_id=request_id)
        return self._to_brief(self._require_request_record(request_id))

    def list_requests_for_user(self, *, requester_user: Any, view: str, limit: int = 100, status: str | None = None) -> dict:
        clean_view = str(view or "mine").strip().lower()
        clean_status = self._normalize_request_status_filter(status)
        is_admin = self._is_admin(requester_user)
        if clean_view == "mine":
            items = self._store.list_requests(
                applicant_user_id=str(requester_user.user_id),
                status=clean_status,
                limit=limit,
            )
        elif clean_view == "todo":
            items = self._store.list_requests(
                related_approver_user_id=str(requester_user.user_id),
                status=clean_status,
                limit=limit,
            )
        elif clean_view == "all":
            if not is_admin:
                raise OperationApprovalServiceError("admin_required", status_code=403)
            items = self._store.list_requests(
                include_all=True,
                status=clean_status,
                company_id=self._normalize_company_id(getattr(requester_user, "company_id", None)),
                limit=limit,
            )
        else:
            raise OperationApprovalServiceError("operation_request_view_invalid", status_code=400)
        return {"items": [self._to_brief(item) for item in items], "count": len(items)}

    def list_todos_for_user(self, *, requester_user: Any, limit: int = 100) -> dict:
        items = self._store.list_requests(pending_approver_user_id=str(requester_user.user_id), limit=limit)
        return {"items": [self._to_brief(item) for item in items], "count": len(items)}

    def get_request_detail_for_user(self, *, request_id: str, requester_user: Any) -> dict:
        request_record = self._require_request_record(request_id)
        if not self._request_visible_to_user(request_data=request_record, requester_user=requester_user):
            raise OperationApprovalServiceError("operation_request_not_visible", status_code=403)
        data = request_record.to_dict()
        data["operation_label"] = self.operation_label(request_record.operation_type)
        data["applicant_full_name"] = self._resolve_user_full_name(request_record.applicant_user_id)
        data["steps"] = self._enrich_request_steps(request_record.steps)
        data["events"] = self._enrich_request_events(request_record.events)
        return data

    def get_stats_for_user(self, *, requester_user: Any) -> dict:
        statuses = (
            REQUEST_STATUS_IN_APPROVAL,
            REQUEST_STATUS_EXECUTED,
            REQUEST_STATUS_REJECTED,
            REQUEST_STATUS_EXECUTION_FAILED,
        )
        if self._is_admin(requester_user):
            counts = self._store.count_requests_by_statuses_for_company(
                statuses=statuses,
                company_id=self._normalize_company_id(getattr(requester_user, "company_id", None)),
            )
        else:
            counts = self._store.count_requests_by_statuses_for_user_visibility(
                statuses=statuses,
                user_id=str(requester_user.user_id),
            )
        return {
            "in_approval_count": int(counts.get(REQUEST_STATUS_IN_APPROVAL, 0)),
            "executed_count": int(counts.get(REQUEST_STATUS_EXECUTED, 0)),
            "rejected_count": int(counts.get(REQUEST_STATUS_REJECTED, 0)),
            "execution_failed_count": int(counts.get(REQUEST_STATUS_EXECUTION_FAILED, 0)),
        }

    def migrate_legacy_document_reviews(self) -> dict:
        return self._migration_service.migrate_legacy_document_reviews()

    def _build_signature_payload(
        self,
        *,
        request_data: dict | ApprovalRequestRecord,
        action: str,
        step_no: int,
        before_status: str,
        after_status: str,
    ):
        request_record = self._to_request_record(request_data)
        return {
            "request_id": request_record.request_id,
            "operation_type": request_record.operation_type,
            "operation_label": self.operation_label(request_record.operation_type),
            "action": action,
            "step_no": step_no,
            "before_status": before_status,
            "after_status": after_status,
            "target_ref": request_record.target_ref,
            "target_label": request_record.target_label,
        }

    def _require_signature_service(self):
        if self._signature_service is None:
            raise OperationApprovalServiceError("electronic_signature_service_unavailable", status_code=500)
        return self._signature_service

    def _load_pending_approval_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        conn: Any | None = None,
    ) -> tuple[dict, dict, dict]:
        return self._decision_service.load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            conn=conn,
        )

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
        actor_user_id = str(actor_user.user_id)
        actor_username = str(actor_user.username)
        request_data, active_step, _ = self._load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
        )
        projected = self._decision_service.project_approval_outcome(
            request_data=request_data,
            active_step=active_step,
        )

        signature_service = self._require_signature_service()
        try:
            signing_context = signature_service.consume_sign_token(
                user=actor_user,
                sign_token=sign_token,
                action="operation_approval_approve",
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

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
                    step_no=active_step.step_no,
                    before_status=request_data.status,
                    after_status=projected.after_status,
                ),
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

        transition = self._store.run_in_transaction(
            lambda conn: self._approve_request_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                notes=notes,
                signature_id=str(signature.signature_id),
                conn=conn,
            )
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data.to_dict(),
            action="operation_approval_approve",
            reason=signature_reason,
            signature_id=str(signature.signature_id),
            step_no=active_step.step_no,
            meta={"signature_meaning": signature_meaning},
        )
        if transition.notify_step_started:
            self._notify_step_started(transition.request_data.to_dict())
        if transition.execute_request:
            self._execute_request(request_id=request_id)
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user=actor_user,
        )

    def _approve_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        notes: str | None,
        signature_id: str,
        conn: Any,
    ) -> dict:
        return self._decision_service.approve_request_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            notes=notes,
            signature_id=signature_id,
            conn=conn,
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
        actor_user_id = str(actor_user.user_id)
        actor_username = str(actor_user.username)
        request_data, active_step, _ = self._load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
        )

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
                    step_no=active_step.step_no,
                    before_status=request_data.status,
                    after_status=REQUEST_STATUS_REJECTED,
                ),
            )
        except ElectronicSignatureError as exc:
            raise OperationApprovalServiceError(exc.code, status_code=exc.status_code) from exc

        final_request = self._store.run_in_transaction(
            lambda conn: self._reject_request_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                notes=notes,
                signature_id=str(signature.signature_id),
                conn=conn,
            )
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data.to_dict(),
            action="operation_approval_reject",
            reason=signature_reason,
            signature_id=str(signature.signature_id),
            step_no=active_step.step_no,
            meta={"signature_meaning": signature_meaning},
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(final_request.to_dict())
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user=actor_user,
        )

    def _reject_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        notes: str | None,
        signature_id: str,
        conn: Any,
    ) -> dict:
        return self._decision_service.reject_request_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            notes=notes,
            signature_id=signature_id,
            conn=conn,
        )

    def withdraw_request(self, *, request_id: str, actor_user: Any, reason: str | None) -> dict:
        request_data = self._require_request_record(request_id)
        is_admin = bool(str(getattr(actor_user, "role", "") or "") == "admin")
        if is_admin and not self._request_visible_to_user(request_data=request_data, requester_user=actor_user):
            raise OperationApprovalServiceError("operation_request_not_visible", status_code=403)
        if request_data.status != REQUEST_STATUS_IN_APPROVAL:
            raise OperationApprovalServiceError("operation_request_not_withdrawable", status_code=409)
        actor_user_id = str(actor_user.user_id)
        actor_username = str(actor_user.username)
        if not is_admin and request_data.applicant_user_id != actor_user_id:
            raise OperationApprovalServiceError("operation_request_withdraw_forbidden", status_code=403)
        final_request = self._store.run_in_transaction(
            lambda conn: self._withdraw_request_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                is_admin=is_admin,
                reason=reason,
                conn=conn,
            )
        )
        self._audit_action(
            actor_user=actor_user,
            request_data=request_data.to_dict(),
            action="operation_approval_withdraw",
            reason=reason,
            signature_id=None,
            step_no=request_data.current_step_no,
            meta={},
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(final_request.to_dict())
        return self.get_request_detail_for_user(
            request_id=request_id,
            requester_user=actor_user,
        )

    def _withdraw_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        is_admin: bool,
        reason: str | None,
        conn: Any,
    ) -> dict:
        return self._decision_service.withdraw_request_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            is_admin=is_admin,
            reason=reason,
            conn=conn,
        )

    def _resolve_execution_deps(self, *, request_data: dict | ApprovalRequestRecord) -> Any:
        request_record = self._to_request_record(request_data)
        company_id = request_record.company_id
        if company_id is None or self._execution_deps_resolver is None:
            return self._deps
        return self._execution_deps_resolver(company_id)

    def _execute_request(self, *, request_id: str) -> None:
        request_data = self._require_request_record(request_id)
        self._execution_service.execute_request(request_id=request_id, request_data=request_data.to_dict())

    def _audit_submit(self, *, ctx: Any, created: dict) -> None:
        self._audit_service.audit_submit(ctx=ctx, created=created)

    def _notify_submission(self, request_data: dict) -> None:
        self._notification_coordinator.notify_submission(request_data)

    def _notify_step_started(self, request_data: dict) -> None:
        self._notification_coordinator.notify_step_started(request_data)

    def _notify_final(self, request_data: dict) -> None:
        self._notification_coordinator.notify_final(request_data)

    def _cleanup_artifacts(self, *, request_id: str) -> None:
        request_data = self._require_request_record(request_id)
        for artifact in request_data.artifacts:
            artifact_id = str(artifact.artifact_id or "")
            file_path = artifact.file_path
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
                    step_no=request_data.current_step_no,
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
        self._audit_service.audit_action(
            actor_user=actor_user,
            request_data=request_data,
            action=action,
            reason=reason,
            signature_id=signature_id,
            step_no=step_no,
            meta=meta,
        )

    def _audit_execute(
        self,
        *,
        request_data: dict,
        applicant_user: Any,
        action: str,
        meta: dict,
        deps: Any | None = None,
    ) -> None:
        self._audit_service.audit_execute(
            request_data=request_data,
            applicant_user=applicant_user,
            action=action,
            meta=meta,
            deps=deps,
        )
