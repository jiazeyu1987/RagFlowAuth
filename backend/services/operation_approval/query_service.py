from __future__ import annotations

from typing import Any, Protocol

from .store import OperationApprovalStore
from .types import (
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    SUPPORTED_OPERATION_TYPES,
    ApprovalRequestEventRecord,
    ApprovalRequestRecord,
    ApprovalRequestStepRecord,
    ApprovalWorkflowRecord,
)


class OperationApprovalQuerySupport(Protocol):
    def operation_label(self, operation_type: str) -> str: ...

    def _is_admin(self, user: Any) -> bool: ...

    def _normalize_company_id(self, value: Any) -> int | None: ...

    def _normalize_request_status_filter(self, status: str | None) -> str | None: ...

    def _require_supported_operation_type(self, operation_type: str) -> str: ...

    def _to_brief(self, item: dict | ApprovalRequestRecord) -> dict: ...

    def _to_workflow_record(
        self,
        workflow_data: dict | ApprovalWorkflowRecord,
    ) -> ApprovalWorkflowRecord: ...

    def _enrich_workflow(self, workflow: dict) -> dict: ...

    def _require_request_record(self, request_id: str) -> ApprovalRequestRecord: ...

    def _request_visible_to_user(
        self,
        *,
        request_data: dict | ApprovalRequestRecord,
        requester_user: Any,
    ) -> bool: ...

    def _resolve_user_full_name(
        self,
        user_id: str | None,
        user_cache: dict[str, Any] | None = None,
    ) -> str | None: ...

    def _enrich_request_steps(
        self,
        steps: list[dict] | list[ApprovalRequestStepRecord],
    ) -> list[dict]: ...

    def _enrich_request_events(
        self,
        events: list[dict] | list[ApprovalRequestEventRecord],
    ) -> list[dict]: ...


class OperationApprovalQueryService:
    def __init__(
        self,
        *,
        store: OperationApprovalStore,
        support: OperationApprovalQuerySupport,
        error_type: type[Exception],
    ):
        self._store = store
        self._support = support
        self._error_type = error_type

    def list_workflows(self) -> list[dict]:
        configured = {
            workflow.operation_type: workflow
            for workflow in (
                self._support._to_workflow_record(item) for item in self._store.list_workflows()
            )
        }
        items: list[dict] = []
        for operation_type in SUPPORTED_OPERATION_TYPES:
            workflow = configured.get(operation_type)
            if workflow:
                items.append(self._support._enrich_workflow(workflow.to_dict()))
                continue
            operation_label = self._support.operation_label(operation_type)
            items.append(
                {
                    "operation_type": operation_type,
                    "operation_label": operation_label,
                    "name": f"{operation_label}审批流程",
                    "is_configured": False,
                    "is_active": False,
                    "steps": [],
                }
            )
        return items

    def get_workflow(self, *, operation_type: str) -> dict:
        clean_type = self._support._require_supported_operation_type(operation_type)
        workflow = self._store.get_workflow(clean_type)
        if not workflow:
            raise self._error_type("operation_workflow_not_configured", status_code=404)
        return self._support._enrich_workflow(workflow)

    def list_requests_for_user(
        self,
        *,
        requester_user: Any,
        view: str,
        limit: int = 100,
        status: str | None = None,
    ) -> dict:
        clean_view = str(view or "mine").strip().lower()
        clean_status = self._support._normalize_request_status_filter(status)
        is_admin = self._support._is_admin(requester_user)
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
                raise self._error_type("admin_required", status_code=403)
            items = self._store.list_requests(
                include_all=True,
                status=clean_status,
                company_id=self._support._normalize_company_id(
                    getattr(requester_user, "company_id", None)
                ),
                limit=limit,
            )
        else:
            raise self._error_type("operation_request_view_invalid", status_code=400)
        return {"items": [self._support._to_brief(item) for item in items], "count": len(items)}

    def list_todos_for_user(self, *, requester_user: Any, limit: int = 100) -> dict:
        items = self._store.list_requests(
            pending_approver_user_id=str(requester_user.user_id),
            limit=limit,
        )
        return {"items": [self._support._to_brief(item) for item in items], "count": len(items)}

    def get_request_detail_for_user(self, *, request_id: str, requester_user: Any) -> dict:
        request_record = self._support._require_request_record(request_id)
        if not self._support._request_visible_to_user(
            request_data=request_record,
            requester_user=requester_user,
        ):
            raise self._error_type("operation_request_not_visible", status_code=403)
        data = request_record.to_dict()
        data["operation_label"] = self._support.operation_label(request_record.operation_type)
        data["applicant_full_name"] = self._support._resolve_user_full_name(
            request_record.applicant_user_id
        )
        data["steps"] = self._support._enrich_request_steps(request_record.steps)
        data["events"] = self._support._enrich_request_events(request_record.events)
        return data

    def get_stats_for_user(self, *, requester_user: Any) -> dict:
        statuses = (
            REQUEST_STATUS_IN_APPROVAL,
            REQUEST_STATUS_EXECUTED,
            REQUEST_STATUS_REJECTED,
            REQUEST_STATUS_EXECUTION_FAILED,
        )
        if self._support._is_admin(requester_user):
            counts = self._store.count_requests_by_statuses_for_company(
                statuses=statuses,
                company_id=self._support._normalize_company_id(
                    getattr(requester_user, "company_id", None)
                ),
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
