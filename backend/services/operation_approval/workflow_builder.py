from __future__ import annotations

from typing import Any, Callable

from .types import (
    SPECIAL_ROLE_DIRECT_MANAGER,
    SUPPORTED_SPECIAL_ROLES,
    SUPPORTED_WORKFLOW_MEMBER_TYPES,
    WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
    WORKFLOW_MEMBER_TYPE_USER,
    ApprovalWorkflowStepRecord,
)


class OperationApprovalWorkflowBuilder:
    def __init__(
        self,
        *,
        user_store: Any,
        error_factory: Callable[[str, int], Exception],
    ) -> None:
        self._user_store = user_store
        self._error_factory = error_factory

    def build_workflow_steps(self, *, steps: list[dict]) -> list[dict]:
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

    def materialize_request_steps(
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
