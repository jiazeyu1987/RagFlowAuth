from __future__ import annotations

from typing import Any, Callable

from .types import (
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    ApprovalRequestRecord,
)


class OperationApprovalExecutionService:
    def __init__(
        self,
        *,
        store: Any,
        handler_registry: dict[str, Any],
        get_user: Callable[[str], Any],
        resolve_execution_deps: Callable[[dict], Any],
        audit_execute: Callable[..., None],
        cleanup_artifacts: Callable[..., None],
        notify_final: Callable[[dict], None],
        transition_request_to_executing_state: Callable[..., dict],
        finalize_request_execution_state: Callable[..., dict],
        error_factory: Callable[[str, int], Exception],
    ):
        self._store = store
        self._handler_registry = handler_registry
        self._get_user = get_user
        self._resolve_execution_deps = resolve_execution_deps
        self._audit_execute = audit_execute
        self._cleanup_artifacts = cleanup_artifacts
        self._notify_final = notify_final
        self._transition_request_to_executing_state = transition_request_to_executing_state
        self._finalize_request_execution_state = finalize_request_execution_state
        self._error_factory = error_factory

    @staticmethod
    def _request_payload(request_data: dict | ApprovalRequestRecord) -> dict:
        if isinstance(request_data, ApprovalRequestRecord):
            return request_data.to_dict()
        return dict(request_data)

    def execute_request(self, *, request_id: str, request_data: dict) -> None:
        request_payload = self._request_payload(request_data)
        handler = self._handler_registry.get(str(request_payload["operation_type"]))
        if handler is None:
            raise self._error_factory("operation_handler_not_configured", 500)
        applicant_user = self._get_user(str(request_payload["applicant_user_id"]))
        started_request = self._store.run_in_transaction(
            lambda conn: self._transition_request_to_executing_state(
                request_id=request_id,
                applicant_user=applicant_user,
                conn=conn,
            )
        )
        started_request_payload = self._request_payload(started_request)
        execution_deps = None
        try:
            execution_deps = self._resolve_execution_deps(started_request_payload)
            self._audit_execute(
                request_data=started_request_payload,
                applicant_user=applicant_user,
                action="operation_approval_execute_start",
                meta={},
                deps=execution_deps,
            )
            result = handler.execute_request(
                request_data=started_request_payload,
                deps=execution_deps,
                applicant_user=applicant_user,
            )
        except Exception as exc:
            code = str(exc) or exc.__class__.__name__
            failed_request = self._store.run_in_transaction(
                lambda conn: self._finalize_request_execution_state(
                    request_id=request_id,
                    applicant_user=applicant_user,
                    status=REQUEST_STATUS_EXECUTION_FAILED,
                    event_type="execution_failed",
                    payload={"error": code},
                    completed=True,
                    last_error=code,
                    conn=conn,
                )
            )
            self._audit_execute(
                request_data=started_request_payload,
                applicant_user=applicant_user,
                action="operation_approval_execute_failed",
                meta={"error": code},
                deps=execution_deps,
            )
            self._cleanup_artifacts(request_id=request_id)
            self._notify_final(self._request_payload(failed_request))
            return
        completed_request = self._store.run_in_transaction(
            lambda conn: self._finalize_request_execution_state(
                request_id=request_id,
                applicant_user=applicant_user,
                status=REQUEST_STATUS_EXECUTED,
                event_type="execution_completed",
                payload=result,
                completed=True,
                executed=True,
                conn=conn,
            )
        )
        self._audit_execute(
            request_data=started_request_payload,
            applicant_user=applicant_user,
            action="operation_approval_execute_success",
            meta=result,
            deps=execution_deps,
        )
        self._cleanup_artifacts(request_id=request_id)
        self._notify_final(self._request_payload(completed_request))
