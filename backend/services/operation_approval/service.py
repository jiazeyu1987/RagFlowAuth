from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from .action_service import OperationApprovalActionService
from .audit_service import OperationApprovalAuditService
from .decision_service import OperationApprovalDecisionService
from .execution_service import OperationApprovalExecutionService
from .handlers import HANDLER_REGISTRY
from .migration_service import OperationApprovalMigrationService
from .notification_service import OperationApprovalNotificationService
from .query_service import OperationApprovalQueryService
from .service_support import OperationApprovalServiceSupport
from .store import OperationApprovalStore


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
        external_notification_service: Any | None = None,
        electronic_signature_service: Any | None = None,
        deps: Any | None = None,
        execution_deps_resolver: Callable[[int | str], Any] | None = None,
    ):
        self._store = store
        self._user_store = user_store
        self._inbox_service = inbox_service
        self._notification_service = notification_service
        self._external_notification_service = external_notification_service or notification_service
        self._signature_service = electronic_signature_service
        self._deps = deps
        self._execution_deps_resolver = execution_deps_resolver

        def error_factory(code: str, status_code: int = 400) -> OperationApprovalServiceError:
            return OperationApprovalServiceError(code, status_code=status_code)

        self._support = OperationApprovalServiceSupport(
            store=store,
            user_store=user_store,
            signature_service=electronic_signature_service,
            deps=deps,
            execution_deps_resolver=execution_deps_resolver,
            error_factory=error_factory,
        )
        self._decision_service = OperationApprovalDecisionService(
            store=store,
            error_factory=error_factory,
        )
        self._audit_service = OperationApprovalAuditService(
            deps=deps,
            brief_resolver=self._support._to_brief,
        )
        self._notification_coordinator = OperationApprovalNotificationService(
            store=store,
            user_store=user_store,
            notification_service=notification_service,
            external_notification_service=self._external_notification_service,
            operation_label_resolver=self.operation_label,
        )
        self._execution_service = OperationApprovalExecutionService(
            store=store,
            handler_registry=HANDLER_REGISTRY,
            get_user=self._support._get_user,
            resolve_execution_deps=lambda request_data: self._support._resolve_execution_deps(
                request_data=request_data
            ),
            audit_execute=self._audit_execute,
            cleanup_artifacts=self._support._cleanup_artifacts,
            notify_final=self._notify_final,
            transition_request_to_executing_state=self._decision_service.transition_request_to_executing_state,
            finalize_request_execution_state=self._decision_service.finalize_request_execution_state,
            error_factory=error_factory,
        )
        self._migration_service = OperationApprovalMigrationService(
            store=store,
            user_store=user_store,
            deps=deps,
            get_user=self._support._get_user,
            resolve_user=self._support._resolve_user,
            get_user_by_username=self._support._get_user_by_username,
            normalize_company_id=self._support._normalize_company_id,
            error_factory=error_factory,
            error_type=OperationApprovalServiceError,
        )
        self._query_service = OperationApprovalQueryService(
            store=store,
            support=self._support,
            error_type=OperationApprovalServiceError,
        )
        self._action_service = OperationApprovalActionService(
            store=store,
            decision_service=self._decision_service,
            migration_service=self._migration_service,
            handler_registry=HANDLER_REGISTRY,
            support=self._support,
            request_id_factory=lambda: uuid4(),
            detail_loader=lambda **kwargs: self._query_service.get_request_detail_for_user(**kwargs),
            audit_submit=self._audit_submit,
            audit_action=self._audit_action,
            notify_submission=self._notify_submission,
            notify_step_started=self._notify_step_started,
            notify_final=self._notify_final,
            cleanup_artifacts=self._support._cleanup_artifacts,
            execute_request=self._execute_request,
            error_type=OperationApprovalServiceError,
        )

    @staticmethod
    def operation_label(operation_type: str) -> str:
        return OperationApprovalServiceSupport.operation_label(operation_type)

    def upsert_workflow(self, *, operation_type: str, name: str | None, steps: list[dict]) -> dict:
        return self._action_service.upsert_workflow(
            operation_type=operation_type,
            name=name,
            steps=steps,
        )

    def list_workflows(self) -> list[dict]:
        return self._query_service.list_workflows()

    def get_workflow(self, *, operation_type: str) -> dict:
        return self._query_service.get_workflow(operation_type=operation_type)

    async def create_request(self, *, operation_type: str, ctx: Any, **kwargs) -> dict:
        return await self._action_service.create_request(
            operation_type=operation_type,
            ctx=ctx,
            **kwargs,
        )

    def list_requests_for_user(
        self,
        *,
        requester_user: Any,
        view: str,
        limit: int = 100,
        status: str | None = None,
    ) -> dict:
        return self._query_service.list_requests_for_user(
            requester_user=requester_user,
            view=view,
            limit=limit,
            status=status,
        )

    def list_todos_for_user(self, *, requester_user: Any, limit: int = 100) -> dict:
        return self._query_service.list_todos_for_user(
            requester_user=requester_user,
            limit=limit,
        )

    def get_request_detail_for_user(self, *, request_id: str, requester_user: Any) -> dict:
        return self._query_service.get_request_detail_for_user(
            request_id=request_id,
            requester_user=requester_user,
        )

    def get_stats_for_user(self, *, requester_user: Any) -> dict:
        return self._query_service.get_stats_for_user(requester_user=requester_user)

    def migrate_legacy_document_reviews(self) -> dict:
        return self._action_service.migrate_legacy_document_reviews()

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
        return self._action_service.approve_request(
            request_id=request_id,
            actor_user=actor_user,
            sign_token=sign_token,
            signature_meaning=signature_meaning,
            signature_reason=signature_reason,
            notes=notes,
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
        return self._action_service.reject_request(
            request_id=request_id,
            actor_user=actor_user,
            sign_token=sign_token,
            signature_meaning=signature_meaning,
            signature_reason=signature_reason,
            notes=notes,
        )

    def withdraw_request(self, *, request_id: str, actor_user: Any, reason: str | None) -> dict:
        return self._action_service.withdraw_request(
            request_id=request_id,
            actor_user=actor_user,
            reason=reason,
        )

    def _execute_request(self, *, request_id: str) -> None:
        request_record = self._support._require_request_record(request_id)
        self._execution_service.execute_request(
            request_id=request_id,
            request_data=request_record.to_dict(),
        )

    def _audit_submit(self, *, ctx: Any, created: dict) -> None:
        self._audit_service.audit_submit(ctx=ctx, created=created)

    def _notify_submission(self, request_data: dict) -> None:
        self._notification_coordinator.notify_submission(request_data)

    def _notify_step_started(self, request_data: dict) -> None:
        self._notification_coordinator.notify_step_started(request_data)

    def _notify_final(self, request_data: dict) -> None:
        self._notification_coordinator.notify_final(request_data)

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
