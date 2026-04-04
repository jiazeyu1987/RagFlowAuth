from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from backend.database.sqlite import connect_sqlite
from backend.services.audit_helpers import actor_fields_from_ctx, actor_fields_from_user
from backend.services.electronic_signature import ElectronicSignatureError
from backend.services.users import resolve_login_block

from .handlers import HANDLER_REGISTRY
from .store import OperationApprovalStore
from .types import (
    APPROVAL_RULE_ALL,
    APPROVAL_RULE_ANY,
    APPROVER_STATUS_APPROVED,
    APPROVER_STATUS_PENDING,
    APPROVER_STATUS_REJECTED,
    INTERNAL_OPERATION_TYPE_LEGACY_DOCUMENT_REVIEW,
    OPERATION_TYPE_LABELS,
    REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    REQUEST_STATUS_EXECUTING,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
    SPECIAL_ROLE_DIRECT_MANAGER,
    SPECIAL_ROLE_LABELS,
    SUPPORTED_REQUEST_STATUSES,
    SUPPORTED_SPECIAL_ROLES,
    SUPPORTED_WORKFLOW_MEMBER_TYPES,
    STEP_STATUS_ACTIVE,
    STEP_STATUS_APPROVED,
    STEP_STATUS_REJECTED,
    SUPPORTED_OPERATION_TYPES,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
    WORKFLOW_MEMBER_TYPE_USER,
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

    def _request_visible_to_user(self, *, request_data: dict, requester_user: Any) -> bool:
        requester_user_id = str(getattr(requester_user, "user_id", "") or "").strip()
        if not requester_user_id:
            return False
        if self._is_admin(requester_user):
            requester_company_id = self._normalize_company_id(getattr(requester_user, "company_id", None))
            request_company_id = self._normalize_company_id(request_data.get("company_id"))
            if requester_company_id is None:
                return True
            return request_company_id == requester_company_id
        approver_request_ids = set(self._store.list_request_ids_for_user(user_id=requester_user_id))
        return request_data["applicant_user_id"] == requester_user_id or request_data["request_id"] in approver_request_ids

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
        member_type = str(member.get("member_type") or "")
        member_ref = str(member.get("member_ref") or "")
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
        item = dict(workflow)
        item["operation_label"] = self.operation_label(item["operation_type"])
        item["is_configured"] = True
        steps: list[dict] = []
        for step in workflow.get("steps") or []:
            steps.append(
                {
                    "workflow_step_id": step.get("workflow_step_id"),
                    "step_no": int(step["step_no"]),
                    "step_name": step["step_name"],
                    "members": [self._workflow_member_view(member) for member in (step.get("members") or [])],
                }
            )
        item["steps"] = steps
        return item

    def _enrich_request_steps(self, steps: list[dict]) -> list[dict]:
        user_cache: dict[str, Any] = {}

        def resolve_full_name(user_id: str | None) -> str | None:
            clean_user_id = str(user_id or "").strip()
            if not clean_user_id:
                return None
            if clean_user_id not in user_cache:
                user_cache[clean_user_id] = self._user_store.get_by_user_id(clean_user_id)
            user = user_cache[clean_user_id]
            full_name = getattr(user, "full_name", None) if user is not None else None
            normalized = str(full_name or "").strip()
            return normalized or None

        enriched_steps: list[dict] = []
        for step in steps or []:
            next_step = dict(step)
            next_step["approvers"] = []
            for approver in step.get("approvers") or []:
                next_approver = dict(approver)
                next_approver["approver_full_name"] = resolve_full_name(approver.get("approver_user_id"))
                next_step["approvers"].append(next_approver)
            enriched_steps.append(next_step)
        return enriched_steps

    def _enrich_request_events(self, events: list[dict]) -> list[dict]:
        user_cache: dict[str, Any] = {}

        def resolve_full_name(user_id: str | None) -> str | None:
            clean_user_id = str(user_id or "").strip()
            if not clean_user_id:
                return None
            if clean_user_id not in user_cache:
                user_cache[clean_user_id] = self._user_store.get_by_user_id(clean_user_id)
            user = user_cache[clean_user_id]
            full_name = getattr(user, "full_name", None) if user is not None else None
            normalized = str(full_name or "").strip()
            return normalized or None

        enriched_events: list[dict] = []
        for event in events or []:
            next_event = dict(event)
            next_event["actor_full_name"] = resolve_full_name(event.get("actor_user_id"))
            enriched_events.append(next_event)
        return enriched_events

    def _snapshot_workflow_steps(self, workflow_steps: list[dict]) -> list[dict]:
        steps: list[dict] = []
        for item in workflow_steps or []:
            steps.append(
                {
                    "step_no": int(item["step_no"]),
                    "step_name": str(item["step_name"]),
                    "approval_rule": str(item.get("approval_rule") or APPROVAL_RULE_ALL),
                    "members": [
                        {
                            "member_type": str(member["member_type"]),
                            "member_ref": str(member["member_ref"]),
                        }
                        for member in (item.get("members") or [])
                    ],
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
            resolved_approvers: dict[str, dict] = {}
            for member in item.get("members") or []:
                member_type = str(member.get("member_type") or "")
                member_ref = str(member.get("member_ref") or "")
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
                                "step_no": int(item["step_no"]),
                                "payload": {
                                    "step_name": str(item["step_name"]),
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
                        "step_no": int(item["step_no"]),
                        "step_name": str(item["step_name"]),
                        "approval_rule": str(item.get("approval_rule") or APPROVAL_RULE_ALL),
                        "approvers": list(resolved_approvers.values()),
                    }
                )
                continue
            events.append(
                {
                    "event_type": "step_auto_skipped",
                    "step_no": int(item["step_no"]),
                    "payload": {
                        "step_name": str(item["step_name"]),
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
        workflow_snapshot_steps = self._snapshot_workflow_steps(workflow["steps"])
        materialized_steps, materialization_events = self._materialize_request_steps(
            workflow_steps=workflow["steps"],
            applicant_user=ctx.user,
        )
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
            workflow_snapshot={"name": workflow["name"], "steps": workflow_snapshot_steps},
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
        self._store.add_event(
            request_id=request_id,
            event_type="request_submitted",
            actor_user_id=str(ctx.user.user_id),
            actor_username=str(ctx.user.username),
            step_no=int(created["current_step_no"] or 0) if created.get("current_step_no") is not None else None,
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
        self._notify_submission(self._store.get_request(request_id))
        if created.get("current_step_no") is None:
            self._complete_request_approval(
                request_id=request_id,
                actor_user_id=str(ctx.user.user_id),
                actor_username=str(ctx.user.username),
                step_no=None,
                signature_id=None,
                auto_approved=True,
            )
        return self._to_brief(self._store.get_request(request_id))

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
        request_data = self._require_request_detail(request_id)
        if not self._request_visible_to_user(request_data=request_data, requester_user=requester_user):
            raise OperationApprovalServiceError("operation_request_not_visible", status_code=403)
        data = dict(request_data)
        data["operation_label"] = self.operation_label(data["operation_type"])
        data["steps"] = self._enrich_request_steps(data.get("steps") or [])
        data["events"] = self._enrich_request_events(data.get("events") or [])
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

    def _find_next_step(self, request_data: dict, *, current_step_no: int) -> dict | None:
        for step in request_data.get("steps") or []:
            if int(step["step_no"]) > int(current_step_no):
                return step
        return None

    def _resolve_legacy_actor_user(self, actor: str):
        clean_actor = str(actor or "").strip()
        if not clean_actor:
            return None
        user = self._user_store.get_by_user_id(clean_actor)
        if user is not None:
            return user
        return self._get_user_by_username(clean_actor)

    @staticmethod
    def _legacy_step_matches_user(step: dict, user: Any) -> bool:
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
        if approval_mode == APPROVAL_RULE_ANY:
            return any(conditions)
        return all(conditions)

    def _resolve_legacy_step_approvers(self, *, step: dict, request_company_id: int | None) -> dict[str, dict]:
        resolved: dict[str, dict] = {}
        approver_user_id = str(step.get("approver_user_id") or "").strip()
        if approver_user_id:
            try:
                user = self._resolve_user(approver_user_id)
            except OperationApprovalServiceError:
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
            if not self._legacy_step_matches_user(step, user):
                continue
            resolved[str(user.user_id)] = {
                "approver_user_id": str(user.user_id),
                "approver_username": str(user.username),
            }
        return resolved

    def _import_legacy_document_review(
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
            raise OperationApprovalServiceError("legacy_review_document_not_found", status_code=409)

        applicant_user_id = str(getattr(doc, "uploaded_by", "") or "").strip()
        if not applicant_user_id:
            raise OperationApprovalServiceError("legacy_review_applicant_missing", status_code=409)
        applicant_user = self._get_user(applicant_user_id)
        request_company_id = self._normalize_company_id(getattr(applicant_user, "company_id", None))
        current_step_no = int(legacy_instance["current_step_no"])
        action_map: dict[int, list[dict]] = {}
        for action in actions:
            action_map.setdefault(int(action["step_no"]), []).append(action)

        request_steps: list[dict] = []
        for step in workflow_steps:
            step_no = int(step["step_no"])
            resolved = self._resolve_legacy_step_approvers(step=step, request_company_id=request_company_id)
            step_actions = action_map.get(step_no, [])
            for action in step_actions:
                actor_user = self._resolve_legacy_actor_user(str(action.get("actor") or ""))
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
                raise OperationApprovalServiceError("legacy_review_migration_unresolved_approvers", status_code=500)

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
                actor_user = self._resolve_legacy_actor_user(str(action.get("actor") or ""))
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
            actor_user = self._resolve_legacy_actor_user(str(action.get("actor") or ""))
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
                    raise OperationApprovalServiceError("legacy_review_workflow_not_found", status_code=500)

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
                    self._import_legacy_document_review(
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
                    if isinstance(exc, OperationApprovalServiceError):
                        raise
                    raise OperationApprovalServiceError(code, status_code=int(getattr(exc, "status_code", 500) or 500)) from exc
                migrated += 1
            return {"migrated": migrated, "skipped": skipped}
        finally:
            conn.close()

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

        approval_rule = str(active_step.get("approval_rule") or APPROVAL_RULE_ALL)
        remaining_after_this = self._store.count_pending_approvers(request_step_id=active_step["request_step_id"]) - 1
        next_step = self._find_next_step(request_data, current_step_no=int(active_step["step_no"]))
        after_status = (
            REQUEST_STATUS_IN_APPROVAL
            if ((approval_rule != APPROVAL_RULE_ANY and remaining_after_this > 0) or next_step is not None)
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

        handler = HANDLER_REGISTRY.get(str(request_data["operation_type"]))
        if handler is None:
            raise OperationApprovalServiceError("operation_handler_not_configured", status_code=500)
        try:
            handler.reject_request(
                request_data=request_data,
                deps=self._resolve_execution_deps(request_data=request_data),
                actor_user=actor_user,
                notes=notes,
                signature_id=str(signature.signature_id),
            )
        except Exception as exc:
            code = str(exc) or exc.__class__.__name__
            raise OperationApprovalServiceError(code, status_code=int(getattr(exc, "status_code", 409) or 409)) from exc

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

        if approval_rule == APPROVAL_RULE_ANY:
            auto_completed_count = self._store.mark_remaining_step_approvers(
                request_step_id=active_step["request_step_id"],
                status=APPROVER_STATUS_APPROVED,
                action="auto_approved_by_any_rule",
                notes="legacy_any_rule_auto_completed",
            )
            if auto_completed_count > 0:
                self._store.add_event(
                    request_id=request_id,
                    event_type="step_auto_completed_by_any_rule",
                    actor_user_id=str(actor_user.user_id),
                    actor_username=str(actor_user.username),
                    step_no=int(active_step["step_no"]),
                    payload={"auto_completed_count": auto_completed_count},
                )
            remaining_after_this = 0

        if remaining_after_this > 0:
            return self.get_request_detail_for_user(
                request_id=request_id,
                requester_user=actor_user,
            )

        self._store.set_step_status(request_step_id=active_step["request_step_id"], status=STEP_STATUS_APPROVED, completed=True)
        if next_step is None:
            self._complete_request_approval(
                request_id=request_id,
                actor_user_id=str(actor_user.user_id),
                actor_username=str(actor_user.username),
                step_no=int(active_step["step_no"]),
                signature_id=str(signature.signature_id),
                auto_approved=False,
            )
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
            requester_user=actor_user,
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
            requester_user=actor_user,
        )

    def withdraw_request(self, *, request_id: str, actor_user: Any, reason: str | None) -> dict:
        request_data = self._require_request_detail(request_id)
        is_admin = bool(str(getattr(actor_user, "role", "") or "") == "admin")
        if is_admin and not self._request_visible_to_user(request_data=request_data, requester_user=actor_user):
            raise OperationApprovalServiceError("operation_request_not_visible", status_code=403)
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
            requester_user=actor_user,
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

    def _complete_request_approval(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        step_no: int | None,
        signature_id: str | None,
        auto_approved: bool,
    ) -> None:
        request_data = self._store.get_request(request_id)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
            current_step_no=request_data.get("current_step_no"),
            current_step_name=request_data.get("current_step_name"),
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_approved",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=step_no,
            payload={"signature_id": signature_id, "auto_approved": bool(auto_approved)},
        )
        self._execute_request(request_id=request_id)

    def _resolve_execution_deps(self, *, request_data: dict) -> Any:
        company_id = request_data.get("company_id")
        if company_id is None or self._execution_deps_resolver is None:
            return self._deps
        return self._execution_deps_resolver(company_id)

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
        execution_deps = None
        try:
            execution_deps = self._resolve_execution_deps(request_data=request_data)
            self._audit_execute(
                request_data=request_data,
                applicant_user=applicant_user,
                action="operation_approval_execute_start",
                meta={},
                deps=execution_deps,
            )
            result = handler.execute_request(
                request_data=self._store.get_request(request_id),
                deps=execution_deps,
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
                deps=execution_deps,
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
            deps=execution_deps,
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
        self._notify_external(recipients=recipients, event_type=event_type, request_data=request_data)

    def _notification_payload(
        self,
        *,
        request_data: dict,
        title: str,
        body: str,
        event_type: str,
    ) -> dict:
        return {
            "request_id": request_data["request_id"],
            "operation_type": request_data["operation_type"],
            "status": request_data["status"],
            "target_ref": request_data.get("target_ref"),
            "target_label": request_data.get("target_label"),
            "current_step_no": request_data.get("current_step_no"),
            "current_step_name": request_data.get("current_step_name"),
            "title": title,
            "body": body,
            "link_path": f"/approvals?request_id={request_data['request_id']}",
            "approval_target": {
                "request_id": request_data["request_id"],
                "operation_type": request_data["operation_type"],
                "route_path": f"/approvals?request_id={request_data['request_id']}",
            },
        }

    def _has_enabled_channel_types(self, channel_types: set[str]) -> bool:
        if self._notification_service is None:
            return False
        list_channels = getattr(self._notification_service, "list_channels", None)
        if not callable(list_channels):
            return False
        channels = list_channels(enabled_only=True) or []
        return any(str(item.get("channel_type") or "").strip().lower() in channel_types for item in channels)

    def _notify_inbox(self, *, recipients: list[dict], title: str, body: str, event_type: str, request_data: dict) -> None:
        if not recipients:
            return
        if self._notification_service is None:
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_inbox_failed",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "error": "notification_service_unavailable"},
            )
            return
        try:
            jobs = self._notification_service.notify_event(
                recipients=recipients,
                event_type=event_type,
                payload=self._notification_payload(
                    request_data=request_data,
                    title=title,
                    body=body,
                    event_type=event_type,
                ),
                dedupe_key=(
                    f"{event_type}:{request_data['request_id']}:in_app:"
                    f"{request_data.get('current_step_no') or 0}:{request_data.get('status')}"
                ),
                channel_types=["in_app"],
            )
            if not jobs:
                self._store.add_event(
                    request_id=request_data["request_id"],
                    event_type="notification_inbox_skipped",
                    actor_user_id=None,
                    actor_username=None,
                    step_no=request_data.get("current_step_no"),
                    payload={"event_type": event_type, "reason": "notification_rule_disabled"},
                )
                return

            for job in jobs:
                self._notification_service.dispatch_job(job_id=int(job["job_id"]))
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_inbox_created",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "recipient_count": len(recipients), "job_count": len(jobs)},
            )
        except Exception as exc:
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_inbox_failed",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "error": str(exc)},
            )

    def _notify_external(self, *, recipients: list[dict], event_type: str, request_data: dict) -> None:
        if not recipients:
            return
        if self._notification_service is None:
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
            jobs = self._notification_service.notify_event(
                payload=self._notification_payload(
                    request_data=request_data,
                    title="",
                    body="",
                    event_type=event_type,
                ),
                recipients=recipients,
                event_type=event_type,
                dedupe_key=(
                    f"{event_type}:{request_data['request_id']}:"
                    f"{request_data.get('current_step_no') or 0}:{request_data.get('status')}"
                ),
                channel_types=["email", "dingtalk"],
            )
            if not jobs:
                self._store.add_event(
                    request_id=request_data["request_id"],
                    event_type="notification_external_skipped",
                    actor_user_id=None,
                    actor_username=None,
                    step_no=request_data.get("current_step_no"),
                    payload={"event_type": event_type, "reason": "notification_rule_disabled"},
                )
                return
            self._store.add_event(
                request_id=request_data["request_id"],
                event_type="notification_external_enqueued",
                actor_user_id=None,
                actor_username=None,
                step_no=request_data.get("current_step_no"),
                payload={"event_type": event_type, "recipient_count": len(recipients), "job_count": len(jobs)},
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

    def _audit_execute(
        self,
        *,
        request_data: dict,
        applicant_user: Any,
        action: str,
        meta: dict,
        deps: Any | None = None,
    ) -> None:
        target_deps = deps if deps is not None else self._deps
        if not target_deps or getattr(target_deps, "audit_log_store", None) is None:
            return
        target_deps.audit_log_store.log_event(
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
