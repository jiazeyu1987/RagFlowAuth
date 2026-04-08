from __future__ import annotations

from typing import Any, Callable, Protocol

from backend.services.electronic_signature import ElectronicSignatureError

from .decision_service import OperationApprovalDecisionService
from .migration_service import OperationApprovalMigrationService
from .store import OperationApprovalStore
from .types import (
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    ApprovalRequestRecord,
    ApprovalWorkflowRecord,
)


class OperationApprovalActionSupport(Protocol):
    def operation_label(self, operation_type: str) -> str: ...

    def _require_supported_operation_type(self, operation_type: str) -> str: ...

    def _build_workflow_steps(self, *, steps: list[dict]) -> list[dict]: ...

    def _enrich_workflow(self, workflow: dict) -> dict: ...

    def _to_workflow_record(
        self,
        workflow_data: dict | ApprovalWorkflowRecord,
    ) -> ApprovalWorkflowRecord: ...

    def _snapshot_workflow_steps(self, workflow_steps: list[dict]) -> list[dict]: ...

    def _materialize_request_steps(
        self,
        *,
        workflow_steps: list[dict],
        applicant_user: Any,
    ) -> tuple[list[dict], list[dict]]: ...

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
    ) -> dict: ...

    def _to_request_record(self, request_data: dict | ApprovalRequestRecord) -> ApprovalRequestRecord: ...

    def _require_request_record(self, request_id: str) -> ApprovalRequestRecord: ...

    def _to_brief(self, item: dict | ApprovalRequestRecord) -> dict: ...

    def _request_visible_to_user(
        self,
        *,
        request_data: dict | ApprovalRequestRecord,
        requester_user: Any,
    ) -> bool: ...

    def _build_signature_payload(
        self,
        *,
        request_data: dict | ApprovalRequestRecord,
        action: str,
        step_no: int,
        before_status: str,
        after_status: str,
    ): ...

    def _require_signature_service(self): ...


class OperationApprovalActionService:
    def __init__(
        self,
        *,
        store: OperationApprovalStore,
        decision_service: OperationApprovalDecisionService,
        migration_service: OperationApprovalMigrationService,
        handler_registry: dict[str, Any],
        support: OperationApprovalActionSupport,
        request_id_factory: Callable[[], Any],
        detail_loader: Callable[..., dict],
        audit_submit: Callable[..., None],
        audit_action: Callable[..., None],
        notify_submission: Callable[[dict], None],
        notify_step_started: Callable[[dict], None],
        notify_final: Callable[[dict], None],
        cleanup_artifacts: Callable[..., None],
        execute_request: Callable[..., None],
        error_type: type[Exception],
    ):
        self._store = store
        self._decision_service = decision_service
        self._migration_service = migration_service
        self._handler_registry = handler_registry
        self._support = support
        self._request_id_factory = request_id_factory
        self._detail_loader = detail_loader
        self._audit_submit = audit_submit
        self._audit_action = audit_action
        self._notify_submission = notify_submission
        self._notify_step_started = notify_step_started
        self._notify_final = notify_final
        self._cleanup_artifacts = cleanup_artifacts
        self._execute_request = execute_request
        self._error_type = error_type

    def upsert_workflow(self, *, operation_type: str, name: str | None, steps: list[dict]) -> dict:
        clean_type = self._support._require_supported_operation_type(operation_type)
        normalized_steps = self._support._build_workflow_steps(steps=steps)
        workflow_name = str(name or "").strip() or f"{self._support.operation_label(clean_type)}审批流程"
        stored = self._store.upsert_workflow(
            operation_type=clean_type,
            name=workflow_name,
            steps=normalized_steps,
        )
        return self._support._enrich_workflow(stored)

    async def create_request(self, *, operation_type: str, ctx: Any, **kwargs) -> dict:
        clean_type = self._support._require_supported_operation_type(operation_type)
        workflow = self._store.get_workflow(clean_type)
        if not workflow or not (workflow.get("steps") or []):
            raise self._error_type("operation_workflow_not_configured", status_code=400)
        workflow_record = self._support._to_workflow_record(workflow)
        handler = self._handler_registry.get(clean_type)
        if handler is None:
            raise self._error_type("operation_handler_not_configured", status_code=500)

        request_id = str(self._request_id_factory())
        prepared = await handler.prepare_request(request_id=request_id, ctx=ctx, **kwargs)
        workflow_snapshot_steps = self._support._snapshot_workflow_steps(workflow_record.steps)
        materialized_steps, materialization_events = self._support._materialize_request_steps(
            workflow_steps=workflow_record.steps,
            applicant_user=ctx.user,
        )
        created = self._store.run_in_transaction(
            lambda conn: self._support._create_request_state(
                request_id=request_id,
                operation_type=clean_type,
                workflow_name=workflow_record.name,
                applicant_user=ctx.user,
                prepared=prepared,
                workflow_snapshot_steps=workflow_snapshot_steps,
                materialized_steps=materialized_steps,
                materialization_events=materialization_events,
                conn=conn,
            )
        )
        created_record = self._support._to_request_record(created)
        self._audit_submit(ctx=ctx, created=created)
        current_request = self._support._require_request_record(request_id)
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
        return self._support._to_brief(self._support._require_request_record(request_id))

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
        request_data, active_step, _ = self._decision_service.load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
        )
        projected = self._decision_service.project_approval_outcome(
            request_data=request_data,
            active_step=active_step,
        )

        signature_service = self._support._require_signature_service()
        try:
            signing_context = signature_service.consume_sign_token(
                user=actor_user,
                sign_token=sign_token,
                action="operation_approval_approve",
            )
        except ElectronicSignatureError as exc:
            raise self._error_type(exc.code, status_code=exc.status_code) from exc

        try:
            signature = signature_service.create_signature(
                signing_context=signing_context,
                user=actor_user,
                record_type="operation_approval_request",
                record_id=str(request_id),
                action="operation_approval_approve",
                meaning=signature_meaning,
                reason=signature_reason,
                record_payload=self._support._build_signature_payload(
                    request_data=request_data,
                    action="approve",
                    step_no=active_step.step_no,
                    before_status=request_data.status,
                    after_status=projected.after_status,
                ),
            )
        except ElectronicSignatureError as exc:
            raise self._error_type(exc.code, status_code=exc.status_code) from exc

        transition = self._store.run_in_transaction(
            lambda conn: self._decision_service.approve_request_state(
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
        return self._detail_loader(request_id=request_id, requester_user=actor_user)

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
        request_data, active_step, _ = self._decision_service.load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
        )

        signature_service = self._support._require_signature_service()
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
                record_payload=self._support._build_signature_payload(
                    request_data=request_data,
                    action="reject",
                    step_no=active_step.step_no,
                    before_status=request_data.status,
                    after_status=REQUEST_STATUS_REJECTED,
                ),
            )
        except ElectronicSignatureError as exc:
            raise self._error_type(exc.code, status_code=exc.status_code) from exc

        final_request = self._store.run_in_transaction(
            lambda conn: self._decision_service.reject_request_state(
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
        return self._detail_loader(request_id=request_id, requester_user=actor_user)

    def withdraw_request(self, *, request_id: str, actor_user: Any, reason: str | None) -> dict:
        request_data = self._support._require_request_record(request_id)
        is_admin = bool(str(getattr(actor_user, "role", "") or "") == "admin")
        if is_admin and not self._support._request_visible_to_user(
            request_data=request_data,
            requester_user=actor_user,
        ):
            raise self._error_type("operation_request_not_visible", status_code=403)
        if request_data.status != REQUEST_STATUS_IN_APPROVAL:
            raise self._error_type("operation_request_not_withdrawable", status_code=409)

        actor_user_id = str(actor_user.user_id)
        actor_username = str(actor_user.username)
        if not is_admin and request_data.applicant_user_id != actor_user_id:
            raise self._error_type("operation_request_withdraw_forbidden", status_code=403)

        final_request = self._store.run_in_transaction(
            lambda conn: self._decision_service.withdraw_request_state(
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
        return self._detail_loader(request_id=request_id, requester_user=actor_user)

    def migrate_legacy_document_reviews(self) -> dict:
        return self._migration_service.migrate_legacy_document_reviews()
