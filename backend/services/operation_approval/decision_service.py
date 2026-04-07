from __future__ import annotations

from typing import Any, Callable

from .types import (
    APPROVAL_RULE_ANY,
    APPROVER_STATUS_APPROVED,
    APPROVER_STATUS_PENDING,
    APPROVER_STATUS_REJECTED,
    REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
    REQUEST_STATUS_EXECUTING,
    REQUEST_STATUS_IN_APPROVAL,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
    STEP_STATUS_ACTIVE,
    STEP_STATUS_APPROVED,
    STEP_STATUS_REJECTED,
    ApprovalOutcomeProjection,
    ApprovalRequestApproverRecord,
    ApprovalRequestRecord,
    ApprovalRequestStepRecord,
    ApprovalStateTransition,
)


class OperationApprovalDecisionService:
    def __init__(self, *, store: Any, error_factory: Callable[[str, int], Exception]):
        self._store = store
        self._error_factory = error_factory

    @staticmethod
    def _request_record(data: dict | ApprovalRequestRecord) -> ApprovalRequestRecord:
        if isinstance(data, ApprovalRequestRecord):
            return data
        return ApprovalRequestRecord.from_dict(data)

    def load_pending_approval_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        conn: Any | None = None,
    ) -> tuple[ApprovalRequestRecord, ApprovalRequestStepRecord, ApprovalRequestApproverRecord]:
        request_data = self._store.get_request(request_id, conn=conn)
        if not request_data:
            raise self._error_factory("operation_request_not_found", 404)
        request_record = ApprovalRequestRecord.from_dict(request_data)
        if request_record.status != REQUEST_STATUS_IN_APPROVAL:
            raise self._error_factory("operation_request_not_active", 409)

        active_step_data = self._store.get_active_step(request_id=request_id, conn=conn)
        if not active_step_data:
            raise self._error_factory("operation_request_active_step_missing", 409)
        active_step = ApprovalRequestStepRecord.from_dict(active_step_data)

        approver_data = self._store.get_step_approver(
            request_id=request_id,
            step_no=active_step.step_no,
            approver_user_id=actor_user_id,
            conn=conn,
        )
        if not approver_data:
            raise self._error_factory("operation_request_not_current_approver", 403)
        approver = ApprovalRequestApproverRecord.from_dict(approver_data)
        if approver.status != APPROVER_STATUS_PENDING:
            raise self._error_factory("operation_request_approver_already_acted", 409)
        return request_record, active_step, approver

    def project_approval_outcome(
        self,
        *,
        request_data: ApprovalRequestRecord,
        active_step: ApprovalRequestStepRecord,
        conn: Any | None = None,
    ) -> ApprovalOutcomeProjection:
        remaining_after_this = self._store.count_pending_approvers(
            request_step_id=str(active_step.request_step_id or ""),
            conn=conn,
        ) - 1
        next_step = request_data.next_step_after(active_step.step_no)
        after_status = (
            REQUEST_STATUS_IN_APPROVAL
            if ((active_step.approval_rule != APPROVAL_RULE_ANY and remaining_after_this > 0) or next_step is not None)
            else REQUEST_STATUS_APPROVED_PENDING_EXECUTION
        )
        return ApprovalOutcomeProjection(
            approval_rule=active_step.approval_rule,
            remaining_after_this=remaining_after_this,
            next_step=next_step,
            after_status=after_status,
        )

    def activate_next_step_state(
        self,
        *,
        request_id: str,
        step_no: int,
        step_name: str,
        actor_user_id: str,
        actor_username: str,
        conn: Any,
        request_data: ApprovalRequestRecord | dict | None = None,
    ) -> ApprovalRequestRecord:
        current_request = self._request_record(request_data) if request_data is not None else None
        if current_request is None:
            current_request_data = self._store.get_request(request_id, conn=conn)
            if not current_request_data:
                raise self._error_factory("operation_request_not_found", 404)
            current_request = ApprovalRequestRecord.from_dict(current_request_data)

        target_step = current_request.find_step(step_no)
        if target_step is None or not target_step.request_step_id:
            raise self._error_factory("operation_request_next_step_missing", 409)

        self._store.set_step_status(
            request_step_id=target_step.request_step_id,
            status=STEP_STATUS_ACTIVE,
            activated=True,
            conn=conn,
        )
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_IN_APPROVAL,
            current_step_no=int(step_no),
            current_step_name=str(step_name),
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="step_activated",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=int(step_no),
            payload={"current_step_name": step_name},
            conn=conn,
        )
        next_request = self._store.get_request(request_id, conn=conn)
        if not next_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(next_request)

    def complete_request_approval_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        step_no: int | None,
        signature_id: str | None,
        auto_approved: bool,
        conn: Any,
        request_data: ApprovalRequestRecord | dict | None = None,
    ) -> ApprovalRequestRecord:
        current_request = self._request_record(request_data) if request_data is not None else None
        if current_request is None:
            current_request_data = self._store.get_request(request_id, conn=conn)
            if not current_request_data:
                raise self._error_factory("operation_request_not_found", 404)
            current_request = ApprovalRequestRecord.from_dict(current_request_data)

        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_APPROVED_PENDING_EXECUTION,
            current_step_no=current_request.current_step_no,
            current_step_name=current_request.current_step_name,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_approved",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=step_no,
            payload={"signature_id": signature_id, "auto_approved": bool(auto_approved)},
            conn=conn,
        )
        next_request = self._store.get_request(request_id, conn=conn)
        if not next_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(next_request)

    def approve_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        notes: str | None,
        signature_id: str,
        conn: Any,
    ) -> ApprovalStateTransition:
        request_data, active_step, _ = self.load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            conn=conn,
        )
        projected = self.project_approval_outcome(
            request_data=request_data,
            active_step=active_step,
            conn=conn,
        )

        self._store.mark_step_approver_action(
            request_id=request_id,
            step_no=active_step.step_no,
            approver_user_id=actor_user_id,
            approver_username=actor_username,
            status=APPROVER_STATUS_APPROVED,
            action="approve",
            notes=notes,
            signature_id=signature_id,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="step_approved_by_user",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=active_step.step_no,
            payload={"notes": notes, "signature_id": signature_id},
            conn=conn,
        )

        remaining_after_this = projected.remaining_after_this
        if projected.approval_rule == APPROVAL_RULE_ANY:
            auto_completed_count = self._store.mark_remaining_step_approvers(
                request_step_id=str(active_step.request_step_id or ""),
                status=APPROVER_STATUS_APPROVED,
                action="auto_approved_by_any_rule",
                notes="legacy_any_rule_auto_completed",
                conn=conn,
            )
            if auto_completed_count > 0:
                self._store.add_event(
                    request_id=request_id,
                    event_type="step_auto_completed_by_any_rule",
                    actor_user_id=actor_user_id,
                    actor_username=actor_username,
                    step_no=active_step.step_no,
                    payload={"auto_completed_count": auto_completed_count},
                    conn=conn,
                )
            remaining_after_this = 0

        if remaining_after_this > 0:
            current_request = self._store.get_request(request_id, conn=conn)
            if not current_request:
                raise self._error_factory("operation_request_not_found", 404)
            return ApprovalStateTransition(
                request_data=ApprovalRequestRecord.from_dict(current_request),
                execute_request=False,
                notify_step_started=False,
            )

        if not active_step.request_step_id:
            raise self._error_factory("operation_request_active_step_missing", 409)
        self._store.set_step_status(
            request_step_id=active_step.request_step_id,
            status=STEP_STATUS_APPROVED,
            completed=True,
            conn=conn,
        )

        if projected.next_step is None:
            current_request = self.complete_request_approval_state(
                request_id=request_id,
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                step_no=active_step.step_no,
                signature_id=signature_id,
                auto_approved=False,
                conn=conn,
                request_data=request_data,
            )
            return ApprovalStateTransition(
                request_data=current_request,
                execute_request=True,
                notify_step_started=False,
            )

        current_request = self.activate_next_step_state(
            request_id=request_id,
            step_no=projected.next_step.step_no,
            step_name=projected.next_step.step_name,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            conn=conn,
            request_data=request_data,
        )
        return ApprovalStateTransition(
            request_data=current_request,
            execute_request=False,
            notify_step_started=True,
        )

    def reject_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        notes: str | None,
        signature_id: str,
        conn: Any,
    ) -> ApprovalRequestRecord:
        _, active_step, _ = self.load_pending_approval_state(
            request_id=request_id,
            actor_user_id=actor_user_id,
            conn=conn,
        )
        self._store.mark_step_approver_action(
            request_id=request_id,
            step_no=active_step.step_no,
            approver_user_id=actor_user_id,
            approver_username=actor_username,
            status=APPROVER_STATUS_REJECTED,
            action="reject",
            notes=notes,
            signature_id=signature_id,
            conn=conn,
        )
        if not active_step.request_step_id:
            raise self._error_factory("operation_request_active_step_missing", 409)
        self._store.set_step_status(
            request_step_id=active_step.request_step_id,
            status=STEP_STATUS_REJECTED,
            completed=True,
            conn=conn,
        )
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_REJECTED,
            current_step_no=active_step.step_no,
            current_step_name=active_step.step_name,
            completed=True,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_rejected",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=active_step.step_no,
            payload={"notes": notes, "signature_id": signature_id},
            conn=conn,
        )
        final_request = self._store.get_request(request_id, conn=conn)
        if not final_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(final_request)

    def withdraw_request_state(
        self,
        *,
        request_id: str,
        actor_user_id: str,
        actor_username: str,
        is_admin: bool,
        reason: str | None,
        conn: Any,
    ) -> ApprovalRequestRecord:
        current_request = self._store.get_request(request_id, conn=conn)
        if not current_request:
            raise self._error_factory("operation_request_not_found", 404)
        request_record = ApprovalRequestRecord.from_dict(current_request)
        if request_record.status != REQUEST_STATUS_IN_APPROVAL:
            raise self._error_factory("operation_request_not_withdrawable", 409)
        if not is_admin and request_record.applicant_user_id != actor_user_id:
            raise self._error_factory("operation_request_withdraw_forbidden", 403)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_WITHDRAWN,
            current_step_no=request_record.current_step_no,
            current_step_name=request_record.current_step_name,
            completed=True,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="request_withdrawn",
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            step_no=request_record.current_step_no,
            payload={"reason": reason},
            conn=conn,
        )
        final_request = self._store.get_request(request_id, conn=conn)
        if not final_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(final_request)

    def transition_request_to_executing_state(
        self,
        *,
        request_id: str,
        applicant_user: Any,
        conn: Any,
    ) -> ApprovalRequestRecord:
        current_request = self._store.get_request(request_id, conn=conn)
        if not current_request:
            raise self._error_factory("operation_request_not_found", 404)
        request_record = ApprovalRequestRecord.from_dict(current_request)
        self._store.set_request_status(
            request_id=request_id,
            status=REQUEST_STATUS_EXECUTING,
            current_step_no=request_record.current_step_no,
            current_step_name=request_record.current_step_name,
            execution_started=True,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type="execution_started",
            actor_user_id=str(applicant_user.user_id),
            actor_username=str(applicant_user.username),
            step_no=request_record.current_step_no,
            payload={},
            conn=conn,
        )
        next_request = self._store.get_request(request_id, conn=conn)
        if not next_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(next_request)

    def finalize_request_execution_state(
        self,
        *,
        request_id: str,
        applicant_user: Any,
        status: str,
        event_type: str,
        payload: dict,
        completed: bool,
        executed: bool = False,
        last_error: str | None = None,
        conn: Any,
    ) -> ApprovalRequestRecord:
        current_request = self._store.get_request(request_id, conn=conn)
        if not current_request:
            raise self._error_factory("operation_request_not_found", 404)
        request_record = ApprovalRequestRecord.from_dict(current_request)
        self._store.set_request_status(
            request_id=request_id,
            status=status,
            current_step_no=request_record.current_step_no,
            current_step_name=request_record.current_step_name,
            completed=completed,
            executed=executed,
            last_error=last_error,
            result_payload=payload,
            conn=conn,
        )
        self._store.add_event(
            request_id=request_id,
            event_type=event_type,
            actor_user_id=str(applicant_user.user_id),
            actor_username=str(applicant_user.username),
            step_no=request_record.current_step_no,
            payload=payload,
            conn=conn,
        )
        next_request = self._store.get_request(request_id, conn=conn)
        if not next_request:
            raise self._error_factory("operation_request_not_found", 404)
        return ApprovalRequestRecord.from_dict(next_request)
