import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.notification import NotificationService, NotificationServiceError, NotificationStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _NoopAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class _CaptureEmailAdapter:
    def __init__(self):
        self.calls: list[dict] = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        return None


class _FlakyEmailAdapter:
    def __init__(self, fail_times: int = 0):
        self.fail_times = int(fail_times)
        self.call_count = 0

    def send(self, **kwargs):  # noqa: ARG002
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise RuntimeError("fake_email_send_failed")
        return None


class _CaptureAuditManager:
    def __init__(self):
        self.events: list[dict] = []

    def log_event(self, **kwargs):
        self.events.append(kwargs)
        return {"id": len(self.events)}


class TestNotificationDispatchUnit(unittest.TestCase):
    @staticmethod
    def _recipient(*, user_id: str = "user-a", username: str = "alice", email: str = "alice@example.com") -> dict:
        return {
            "user_id": user_id,
            "username": username,
            "full_name": username.title(),
            "email": email,
        }

    def test_dispatch_success_and_logs(self):
        td = make_temp_dir(prefix="ragflowauth_notification_success")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=1,
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"to_emails": ["qa@example.com"]},
            )

            jobs = service.notify_event(
                event_type="review_todo_approval",
                payload={"doc_id": "doc-1", "filename": "a.txt", "current_step_name": "Step 1"},
                recipients=[self._recipient()],
                dedupe_key="review_todo_approval:doc-1:step-1",
                max_attempts=2,
                channel_types=["email"],
            )
            self.assertEqual(len(jobs), 1)
            job_id = int(jobs[0]["job_id"])
            self.assertEqual(jobs[0]["status"], "queued")

            dispatched = service.dispatch_pending(limit=10)
            self.assertEqual(dispatched["total"], 1)
            self.assertEqual(dispatched["items"][0]["status"], "sent")

            job = store.get_job(job_id)
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "sent")
            self.assertIsNotNone(job["sent_at_ms"])

            logs = store.list_delivery_logs(job_id=job_id)
            self.assertEqual(len(logs), 2)
            self.assertEqual(logs[0]["status"], "sent")
            self.assertEqual(logs[1]["status"], "queued")
            self.assertIsNone(logs[0]["error"])
        finally:
            cleanup_dir(td)

    def test_failed_job_can_retry(self):
        td = make_temp_dir(prefix="ragflowauth_notification_retry")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            flaky = _FlakyEmailAdapter(fail_times=1)
            service = NotificationService(
                store=store,
                email_adapter=flaky,
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=60,
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"to_emails": ["qa@example.com"]},
            )

            jobs = service.notify_event(
                event_type="review_rejected",
                payload={"doc_id": "doc-2"},
                recipients=[self._recipient()],
                dedupe_key="review_rejected:doc-2",
                max_attempts=2,
                channel_types=["email"],
            )
            job_id = int(jobs[0]["job_id"])
            first = service.dispatch_pending(limit=10)
            self.assertEqual(first["total"], 1)
            self.assertEqual(first["items"][0]["status"], "queued")

            after_first = store.get_job(job_id)
            self.assertIsNotNone(after_first)
            self.assertEqual(after_first["status"], "queued")
            self.assertEqual(after_first["attempts"], 1)
            self.assertEqual(after_first["last_error"], "fake_email_send_failed")
            self.assertIsNotNone(after_first["next_retry_at_ms"])

            retried = service.retry_job(job_id=job_id)
            self.assertEqual(retried["status"], "sent")
            self.assertIsNotNone(retried["sent_at_ms"])

            logs = store.list_delivery_logs(job_id=job_id, limit=10)
            self.assertEqual(len(logs), 4)
            statuses = {x["status"] for x in logs}
            self.assertEqual(statuses, {"queued", "failed", "sent"})
        finally:
            cleanup_dir(td)

    def test_notify_requires_enabled_channel(self):
        td = make_temp_dir(prefix="ragflowauth_notification_no_channel")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
            )
            with self.assertRaises(NotificationServiceError) as ctx:
                service.notify_event(
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-x"},
                    recipients=[self._recipient()],
                    dedupe_key="review_todo_approval:doc-x",
                )
            self.assertEqual(str(ctx.exception), "notification_channel_not_configured:in_app")
        finally:
            cleanup_dir(td)

    def test_notify_event_strictly_fails_when_any_channel_unresolved(self):
        td = make_temp_dir(prefix="ragflowauth_notification_strict_unresolved")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=1,
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "ding-app-key",
                    "app_secret": "ding-app-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {},
                },
            )

            with self.assertRaises(NotificationServiceError) as ctx:
                service.notify_event(
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-strict"},
                    recipients=[self._recipient(user_id="u-strict", username="strict", email="strict@example.com")],
                    dedupe_key="strict:doc-strict",
                    channel_types=["email", "dingtalk"],
                )
            self.assertTrue(str(ctx.exception).startswith("notification_recipient_unresolved"))
            self.assertEqual(len(store.list_jobs(limit=10)), 0)
        finally:
            cleanup_dir(td)

    def test_dingtalk_alias_map_takes_priority_over_org_directory(self):
        td = make_temp_dir(prefix="ragflowauth_notification_dingtalk_alias_priority")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "ding-app-key",
                    "app_secret": "ding-app-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy-user": "ding-target"},
                    "recipient_directory": {
                        "legacy-user": {"full_name": "Legacy User", "company_id": 1, "department_id": 1},
                        "ding-target": {"full_name": "Target User", "company_id": 1, "department_id": 1},
                    },
                },
            )

            jobs = service.notify_event(
                event_type="review_todo_approval",
                payload={"doc_id": "doc-alias-priority"},
                recipients=[self._recipient(user_id="legacy-user", username="legacy-user", email="")],
                dedupe_key="review_todo_approval:doc-alias-priority",
                channel_types=["dingtalk"],
            )

            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["recipient_address"], "ding-target")
        finally:
            cleanup_dir(td)

    def test_dingtalk_org_directory_accepts_direct_user_id_or_username_only(self):
        channel = {
            "channel_type": "dingtalk",
            "config": {
                "recipient_map": {},
                "recipient_directory": {
                    "ding-user": {"full_name": "Ding User", "company_id": 1, "department_id": 1},
                },
            },
        }

        self.assertEqual(
            NotificationService._resolve_recipient_address(
                channel=channel,
                recipient={"user_id": "ding-user", "username": "not-used", "full_name": "Other"},
            ),
            "ding-user",
        )
        self.assertEqual(
            NotificationService._resolve_recipient_address(
                channel=channel,
                recipient={"user_id": "", "username": "ding-user", "full_name": "Other"},
            ),
            "ding-user",
        )
        self.assertIsNone(
            NotificationService._resolve_recipient_address(
                channel=channel,
                recipient={"user_id": "system-user", "username": "system-username", "full_name": "Ding User"},
            )
        )

    def test_dingtalk_org_directory_accepts_explicit_employee_user_id(self):
        channel = {
            "channel_type": "dingtalk",
            "config": {
                "recipient_map": {},
                "recipient_directory": {
                    "ding-user": {"full_name": "Ding User", "company_id": 1, "department_id": 1},
                },
            },
        }

        self.assertEqual(
            NotificationService._resolve_recipient_address(
                channel=channel,
                recipient={
                    "user_id": "system-user",
                    "username": "system-username",
                    "employee_user_id": "ding-user",
                    "full_name": "Ding User",
                },
            ),
            "ding-user",
        )

    def test_in_app_inbox_read_flow_and_audit_logs(self):
        td = make_temp_dir(prefix="ragflowauth_notification_in_app_inbox")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            audit = _CaptureAuditManager()
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
                audit_log_manager=audit,
                retry_interval_seconds=1,
            )
            service.upsert_channel(
                channel_id="inapp-main",
                channel_type="in_app",
                name="In App",
                enabled=True,
                config={},
                audit={"actor": "admin-u1", "source": "notification"},
            )

            jobs = service.notify_event(
                event_type="review_todo_approval",
                payload={"doc_id": "doc-inbox", "filename": "inbox.txt"},
                recipients=[self._recipient(user_id="user-a", username="alice", email="alice@example.com")],
                dedupe_key="inbox:doc-inbox",
                audit={"actor": "system"},
            )
            self.assertEqual(len(jobs), 1)
            job_id = int(jobs[0]["job_id"])
            dispatched = service.dispatch_pending(limit=10, audit={"actor": "system"})
            self.assertEqual(dispatched["total"], 1)
            self.assertEqual(dispatched["items"][0]["status"], "sent")

            inbox = service.list_inbox(recipient_user_id="user-a", limit=20, offset=0, unread_only=False)
            self.assertEqual(inbox["total"], 1)
            self.assertEqual(inbox["unread_count"], 1)
            self.assertEqual(inbox["items"][0]["job_id"], job_id)

            updated = service.update_inbox_read_state(
                job_id=job_id,
                recipient_user_id="user-a",
                read=True,
                audit={"actor": "user-a"},
            )
            self.assertIsNotNone(updated["read_at_ms"])
            unread_after_read = service.list_inbox(recipient_user_id="user-a", unread_only=True)
            self.assertEqual(unread_after_read["unread_count"], 0)

            updated_unread = service.update_inbox_read_state(
                job_id=job_id,
                recipient_user_id="user-a",
                read=False,
                audit={"actor": "user-a"},
            )
            self.assertIsNone(updated_unread["read_at_ms"])

            mark_all_result = service.mark_all_inbox_read(
                recipient_user_id="user-a",
                audit={"actor": "user-a"},
            )
            self.assertEqual(mark_all_result["updated_count"], 1)
            inbox_after_all = service.list_inbox(recipient_user_id="user-a", unread_only=True)
            self.assertEqual(inbox_after_all["unread_count"], 0)

            logs = store.list_delivery_logs(job_id=job_id, limit=20)
            statuses = {item["status"] for item in logs}
            self.assertEqual(statuses, {"queued", "sent", "read", "unread"})

            actions = {event.get("action") for event in audit.events}
            self.assertIn("notification_job_enqueue", actions)
            self.assertIn("notification_job_dispatch", actions)
            self.assertIn("notification_inbox_read_state_update", actions)
            self.assertIn("notification_inbox_mark_all_read", actions)
        finally:
            cleanup_dir(td)

    def test_duplicate_suppression_and_manual_resend(self):
        td = make_temp_dir(prefix="ragflowauth_notification_dedupe")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            capture = _CaptureEmailAdapter()
            service = NotificationService(
                store=store,
                email_adapter=capture,
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=1,
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
            )

            payload = {
                "doc_id": "doc-r5",
                "filename": "batch-spec.pdf",
                "current_step_name": "QA review",
                "approval_target": {"route_path": "/documents?tab=approve&doc_id=doc-r5"},
            }
            first = service.notify_event(
                event_type="review_todo_approval",
                payload=payload,
                recipients=[self._recipient()],
                dedupe_key="review_todo_approval:doc-r5:step-1",
                channel_types=["email"],
            )
            second = service.notify_event(
                event_type="review_todo_approval",
                payload=payload,
                recipients=[self._recipient()],
                dedupe_key="review_todo_approval:doc-r5:step-1",
                channel_types=["email"],
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertEqual(first[0]["job_id"], second[0]["job_id"])
            self.assertEqual(len(store.list_jobs(limit=10)), 1)

            sent = service.dispatch_pending(limit=10)
            self.assertEqual(sent["total"], 1)
            self.assertEqual(sent["items"][0]["status"], "sent")

            resent = service.resend_job(job_id=int(first[0]["job_id"]))
            self.assertEqual(resent["status"], "sent")
            self.assertEqual(len(store.list_jobs(limit=10)), 2)
            self.assertEqual(resent["source_job_id"], int(first[0]["job_id"]))
            self.assertEqual(len(capture.calls), 2)
            self.assertEqual(capture.calls[0]["recipient"]["address"], "alice@example.com")
            self.assertEqual(capture.calls[0]["payload"]["current_step_name"], "QA review")
            self.assertEqual(capture.calls[0]["payload"]["filename"], "batch-spec.pdf")
            self.assertEqual(
                capture.calls[0]["payload"]["approval_target"]["route_path"],
                "/documents?tab=approve&doc_id=doc-r5",
            )
        finally:
            cleanup_dir(td)

    def test_event_rules_support_disable_and_missing_channel_fail_fast(self):
        td = make_temp_dir(prefix="ragflowauth_notification_rules")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopAdapter(),
                dingtalk_adapter=_NoopAdapter(),
                retry_interval_seconds=1,
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"host": "smtp.example.com", "from_email": "noreply@example.com"},
            )

            rules = service.list_event_rules()
            review_rule = None
            for group in rules["groups"]:
                for item in group["items"]:
                    if item["event_type"] == "review_todo_approval":
                        review_rule = item
                        break
            self.assertIsNotNone(review_rule)
            self.assertEqual(review_rule["enabled_channel_types"], ["in_app", "email"])
            self.assertTrue(review_rule["has_enabled_channel_config_by_type"]["email"])
            self.assertFalse(review_rule["has_enabled_channel_config_by_type"]["in_app"])

            service.upsert_event_rules(
                items=[{"event_type": "review_todo_approval", "enabled_channel_types": []}],
            )
            skipped = service.notify_event(
                event_type="review_todo_approval",
                payload={"doc_id": "doc-disabled"},
                recipients=[self._recipient()],
                dedupe_key="review_todo_approval:doc-disabled",
            )
            self.assertEqual(skipped, [])
            self.assertEqual(len(store.list_jobs(limit=10)), 0)

            service.upsert_event_rules(
                items=[{"event_type": "review_todo_approval", "enabled_channel_types": ["email", "dingtalk"]}],
            )
            with self.assertRaises(NotificationServiceError) as ctx:
                service.notify_event(
                    event_type="review_todo_approval",
                    payload={"doc_id": "doc-missing-channel"},
                    recipients=[self._recipient()],
                    dedupe_key="review_todo_approval:doc-missing-channel",
                )
            self.assertEqual(str(ctx.exception), "notification_channel_not_configured:dingtalk")
        finally:
            cleanup_dir(td)
