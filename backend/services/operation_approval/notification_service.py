from __future__ import annotations

from typing import Any, Callable

from .types import (
    APPROVER_STATUS_PENDING,
    REQUEST_STATUS_EXECUTED,
    REQUEST_STATUS_EXECUTION_FAILED,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_WITHDRAWN,
)


class OperationApprovalNotificationService:
    def __init__(
        self,
        *,
        store: Any,
        user_store: Any,
        notification_service: Any | None = None,
        external_notification_service: Any | None = None,
        operation_label_resolver: Callable[[str], str],
    ):
        self._store = store
        self._user_store = user_store
        self._notification_service = notification_service
        self._external_notification_service = external_notification_service or notification_service
        self._operation_label = operation_label_resolver

    def notify_submission(self, request_data: dict) -> None:
        recipients = self._applicant_recipient(request_data)
        self.notify_external(
            recipients=recipients,
            event_type="operation_approval_submitted",
            request_data=request_data,
        )
        self.notify_step_started(request_data)

    def notify_step_started(self, request_data: dict) -> None:
        recipients = self._recipients_for_step(request_data)
        if not recipients:
            return
        self.notify_inbox(
            recipients=recipients,
            title=f"{self._operation_label(request_data['operation_type'])}待审批",
            body=(
                f"申请单 {request_data['request_id']} 已到第 {request_data.get('current_step_no')} 层："
                f"{request_data.get('current_step_name')}"
            ),
            event_type="operation_approval_todo",
            request_data=request_data,
        )
        self.notify_external(
            recipients=recipients,
            event_type="operation_approval_todo",
            request_data=request_data,
        )

    def notify_final(self, request_data: dict) -> None:
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
        self.notify_external(
            recipients=recipients,
            event_type=event_type,
            request_data=request_data,
        )

    def notify_inbox(
        self,
        *,
        recipients: list[dict],
        title: str,
        body: str,
        event_type: str,
        request_data: dict,
    ) -> None:
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

    def notify_external(self, *, recipients: list[dict], event_type: str, request_data: dict) -> None:
        if not recipients:
            return
        service = self._external_notification_service
        if service is None:
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
            jobs = service.notify_event(
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
            results = [service.dispatch_job(job_id=int(job["job_id"])) for job in jobs]
            failed = [item for item in results if str(item.get("status") or "").strip().lower() != "sent"]
            if failed:
                self._store.add_event(
                    request_id=request_data["request_id"],
                    event_type="notification_external_failed",
                    actor_user_id=None,
                    actor_username=None,
                    step_no=request_data.get("current_step_no"),
                    payload={
                        "event_type": event_type,
                        "job_count": len(jobs),
                        "failed_job_count": len(failed),
                        "error": failed[0].get("last_error"),
                    },
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

    def _recipients_for_step(self, request_data: dict) -> list[dict]:
        current_step_no = request_data.get("current_step_no")
        if current_step_no is None:
            return []
        for step in request_data.get("steps") or []:
            if int(step["step_no"]) != int(current_step_no):
                continue
            recipients: list[dict] = []
            for approver in step.get("approvers") or []:
                if approver.get("status") != APPROVER_STATUS_PENDING:
                    continue
                user = self._user_store.get_by_user_id(approver["approver_user_id"])
                recipients.append(
                    {
                        "user_id": approver["approver_user_id"],
                        "username": approver.get("approver_username"),
                        "employee_user_id": getattr(user, "employee_user_id", None),
                        "email": getattr(user, "email", None),
                    }
                )
            return recipients
        return []

    def _applicant_recipient(self, request_data: dict) -> list[dict]:
        user = self._user_store.get_by_user_id(str(request_data["applicant_user_id"]))
        if not user:
            return []
        return [
            {
                "user_id": str(user.user_id),
                "username": str(user.username),
                "employee_user_id": getattr(user, "employee_user_id", None),
                "email": getattr(user, "email", None),
            }
        ]
