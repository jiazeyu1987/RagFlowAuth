from __future__ import annotations

from typing import Any, Callable

from backend.services.audit_helpers import actor_fields_from_ctx, actor_fields_from_user


class OperationApprovalAuditService:
    def __init__(self, *, deps: Any | None = None, brief_resolver: Callable[[dict], dict] | None = None):
        self._deps = deps
        self._brief_resolver = brief_resolver

    def audit_submit(self, *, ctx: Any, created: dict) -> None:
        if not self._deps or getattr(self._deps, "audit_log_store", None) is None:
            return
        after = self._brief_resolver(created) if self._brief_resolver is not None else created
        self._deps.audit_log_store.log_event(
            action="operation_approval_submit",
            actor=ctx.payload.sub,
            source="operation_approval",
            resource_type="operation_approval_request",
            resource_id=created["request_id"],
            request_id=created["request_id"],
            event_type="create",
            after=after,
            meta={"operation_type": created["operation_type"]},
            **actor_fields_from_ctx(self._deps, ctx),
        )

    def audit_action(
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

    def audit_execute(
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
