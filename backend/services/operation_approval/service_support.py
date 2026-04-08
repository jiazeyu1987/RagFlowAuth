from __future__ import annotations

import os
from typing import Any, Callable

from .store import OperationApprovalStore
from .types import (
    OPERATION_TYPE_LABELS,
    REQUEST_STATUS_IN_APPROVAL,
    SPECIAL_ROLE_DIRECT_MANAGER,
    SPECIAL_ROLE_LABELS,
    SUPPORTED_OPERATION_TYPES,
    SUPPORTED_REQUEST_STATUSES,
    SUPPORTED_SPECIAL_ROLES,
    SUPPORTED_WORKFLOW_MEMBER_TYPES,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
    WORKFLOW_MEMBER_TYPE_USER,
    ApprovalRequestEventRecord,
    ApprovalRequestRecord,
    ApprovalRequestStepRecord,
    ApprovalWorkflowMemberRecord,
    ApprovalWorkflowRecord,
    ApprovalWorkflowStepRecord,
)


class OperationApprovalServiceSupport:
    def __init__(
        self,
        *,
        store: OperationApprovalStore,
        user_store: Any,
        signature_service: Any | None,
        deps: Any | None,
        execution_deps_resolver: Callable[[int | str], Any] | None,
        error_factory: Callable[[str, int], Exception],
    ):
        self._store = store
        self._user_store = user_store
        self._signature_service = signature_service
        self._deps = deps
        self._execution_deps_resolver = execution_deps_resolver
        self._error_factory = error_factory

    @staticmethod
    def operation_label(operation_type: str) -> str:
        return OPERATION_TYPE_LABELS.get(operation_type, operation_type)

    def _require_supported_operation_type(self, operation_type: str) -> str:
        value = str(operation_type or "").strip()
        if value not in SUPPORTED_OPERATION_TYPES:
            raise self._error_factory("operation_type_unsupported", 400)
        return value

    def _normalize_request_status_filter(self, status: str | None) -> str | None:
        value = str(status or "").strip().lower()
        if not value or value == "all":
            return None
        if value not in SUPPORTED_REQUEST_STATUSES:
            raise self._error_factory("operation_request_status_invalid", 400)
        return value

    def _get_user(self, user_id: str):
        user = self._user_store.get_by_user_id(user_id)
        if not user:
            raise self._error_factory("workflow_approver_not_found", 400)
        return user

    def _resolve_user(self, user_id: str):
        user = self._get_user(user_id)
        if str(getattr(user, "status", "") or "").strip().lower() != "active":
            raise self._error_factory("workflow_approver_inactive", 400)
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
            requester_company_id = self._normalize_company_id(
                getattr(requester_user, "company_id", None)
            )
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
            raise self._error_factory("workflow_steps_required", 400)
        normalized: list[dict] = []
        for index, item in enumerate(steps, start=1):
            step_name = str((item or {}).get("step_name") or "").strip()
            if not step_name:
                raise self._error_factory("workflow_step_name_required", 400)
            raw_members = (item or {}).get("members")
            if raw_members is None and (item or {}).get("approver_user_ids") is not None:
                raw_members = [
                    {"member_type": WORKFLOW_MEMBER_TYPE_USER, "member_ref": raw_user_id}
                    for raw_user_id in ((item or {}).get("approver_user_ids") or [])
                ]
            if not isinstance(raw_members, list):
                raise self._error_factory("workflow_step_members_required", 400)
            members: list[dict] = []
            for raw_member in raw_members:
                if not isinstance(raw_member, dict):
                    raise self._error_factory("workflow_step_member_invalid", 400)
                member_type = str(raw_member.get("member_type") or "").strip()
                member_ref = str(raw_member.get("member_ref") or "").strip()
                if member_type not in SUPPORTED_WORKFLOW_MEMBER_TYPES:
                    raise self._error_factory("workflow_step_member_type_invalid", 400)
                if not member_ref:
                    raise self._error_factory("workflow_step_member_ref_required", 400)
                if member_type == WORKFLOW_MEMBER_TYPE_USER:
                    self._resolve_user(member_ref)
                elif member_ref not in SUPPORTED_SPECIAL_ROLES:
                    raise self._error_factory("workflow_step_special_role_invalid", 400)
                members.append({"member_type": member_type, "member_ref": member_ref})
            if not members:
                raise self._error_factory("workflow_step_members_required", 400)
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
        item["steps"] = [
            {
                "workflow_step_id": step.workflow_step_id,
                "step_no": step.step_no,
                "step_name": step.step_name,
                "members": [self._workflow_member_view(member.to_dict()) for member in step.members],
            }
            for step in workflow_record.steps
        ]
        return item

    def _resolve_user_full_name(
        self,
        user_id: str | None,
        user_cache: dict[str, Any] | None = None,
    ) -> str | None:
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
            step_record = (
                step if isinstance(step, ApprovalRequestStepRecord) else ApprovalRequestStepRecord.from_dict(step)
            )
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
            event_record = (
                event if isinstance(event, ApprovalRequestEventRecord) else ApprovalRequestEventRecord.from_dict(event)
            )
            next_event = event_record.to_dict()
            next_event["actor_full_name"] = self._resolve_user_full_name(
                event_record.actor_user_id,
                user_cache,
            )
            enriched_events.append(next_event)
        return enriched_events

    def _snapshot_workflow_steps(self, workflow_steps: list[dict]) -> list[dict]:
        steps: list[dict] = []
        for item in workflow_steps or []:
            step_record = (
                item if isinstance(item, ApprovalWorkflowStepRecord) else ApprovalWorkflowStepRecord.from_dict(item)
            )
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

    def _materialize_request_steps(
        self,
        *,
        workflow_steps: list[dict],
        applicant_user: Any,
    ) -> tuple[list[dict], list[dict]]:
        materialized_steps: list[dict] = []
        events: list[dict] = []
        for item in workflow_steps or []:
            step_record = (
                item if isinstance(item, ApprovalWorkflowStepRecord) else ApprovalWorkflowStepRecord.from_dict(item)
            )
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
                raise self._error_factory("workflow_step_special_role_invalid", 400)
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
            raise self._error_factory("operation_request_not_found", 404)
        return data

    def _require_request_record(self, request_id: str) -> ApprovalRequestRecord:
        return self._to_request_record(self._require_request_detail(request_id))

    def _create_request_state(
        self,
        *,
        request_id: str,
        operation_type: str,
        workflow_name: str,
        applicant_user: Any,
        prepared: Any,
        workflow_snapshot_steps: list[dict],
        materialized_steps: list[dict],
        materialization_events: list[dict],
        conn: Any,
    ) -> dict:
        created = self._store.create_request(
            request_id=request_id,
            operation_type=operation_type,
            workflow_name=workflow_name,
            applicant_user_id=str(applicant_user.user_id),
            applicant_username=str(applicant_user.username),
            company_id=(
                int(applicant_user.company_id)
                if getattr(applicant_user, "company_id", None) is not None
                else None
            ),
            department_id=(
                int(applicant_user.department_id)
                if getattr(applicant_user, "department_id", None) is not None
                else None
            ),
            target_ref=prepared.target_ref,
            target_label=prepared.target_label,
            summary=prepared.summary,
            payload=prepared.payload,
            workflow_snapshot={"name": workflow_name, "steps": workflow_snapshot_steps},
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
            conn=conn,
        )
        created_record = self._to_request_record(created)
        self._store.add_event(
            request_id=request_id,
            event_type="request_submitted",
            actor_user_id=str(applicant_user.user_id),
            actor_username=str(applicant_user.username),
            step_no=created_record.current_step_no,
            payload={
                "operation_type": operation_type,
                "target_ref": prepared.target_ref,
                "target_label": prepared.target_label,
            },
            conn=conn,
        )
        for event in materialization_events:
            self._store.add_event(
                request_id=request_id,
                event_type=str(event["event_type"]),
                actor_user_id=str(applicant_user.user_id),
                actor_username=str(applicant_user.username),
                step_no=event.get("step_no"),
                payload=event.get("payload") or {},
                conn=conn,
            )
        if created_record.current_step_no is not None:
            self._store.add_event(
                request_id=request_id,
                event_type="step_activated",
                actor_user_id=str(applicant_user.user_id),
                actor_username=str(applicant_user.username),
                step_no=created_record.current_step_no,
                payload={"current_step_name": created_record.current_step_name},
                conn=conn,
            )
        return created

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
            raise self._error_factory("electronic_signature_service_unavailable", 500)
        return self._signature_service

    def _resolve_execution_deps(self, *, request_data: dict | ApprovalRequestRecord) -> Any:
        request_record = self._to_request_record(request_data)
        company_id = request_record.company_id
        if company_id is None or self._execution_deps_resolver is None:
            return self._deps
        return self._execution_deps_resolver(company_id)

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
