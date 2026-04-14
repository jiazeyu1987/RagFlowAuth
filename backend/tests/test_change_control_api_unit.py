import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.change_control.router import router as change_control_router
from backend.database.schema.ensure import ensure_schema
from backend.services.change_control import ChangeControlService
from backend.services.inbox_service import UserInboxService
from backend.services.inbox_store import UserInboxStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def __init__(self, users: dict[str, SimpleNamespace]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)


class _Deps:
    def __init__(self, *, db_path: str, users: dict[str, SimpleNamespace]):
        self.user_store = _UserStore(users)
        self.permission_group_store = SimpleNamespace(get_group=lambda *_args, **_kwargs: None)
        self.user_kb_permission_store = SimpleNamespace(get_user_kbs=lambda *_args, **_kwargs: [])
        self.user_chat_permission_store = SimpleNamespace(get_user_chats=lambda *_args, **_kwargs: [])
        self.kb_store = SimpleNamespace(db_path=db_path)
        self.user_inbox_store = UserInboxStore(db_path=db_path)
        self.user_inbox_service = UserInboxService(store=self.user_inbox_store)
        self.change_control_service = ChangeControlService(
            db_path=db_path,
            user_inbox_service=self.user_inbox_service,
        )


def _make_user(*, user_id: str, role: str) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        role=role,
        status="active",
        group_id=None,
        group_ids=[],
        tool_ids=[],
        company_id=1,
        department_id=1,
    )


class TestChangeControlApiUnit(unittest.TestCase):
    def _build_app(self, *, current_user_id: str, deps):
        def _override_get_current_payload(_: Request) -> TokenPayload:
            return TokenPayload(sub=current_user_id)

        app = FastAPI()
        app.state.deps = deps
        app.include_router(change_control_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return app

    def test_full_workflow_with_confirmation_and_close(self):
        td = make_temp_dir(prefix="ragflowauth_change_control_happy")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "owner-1": _make_user(user_id="owner-1", role="sub_admin"),
                "eval-1": _make_user(user_id="eval-1", role="sub_admin"),
                "qa-1": _make_user(user_id="qa-1", role="sub_admin"),
                "ops-1": _make_user(user_id="ops-1", role="sub_admin"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/change-control/requests",
                    json={
                        "title": "WS04 workflow validation",
                        "reason": "Need controlled workflow",
                        "owner_user_id": "owner-1",
                        "evaluator_user_id": "eval-1",
                        "planned_due_date": "2026-04-20",
                        "required_departments": ["qa", "ops"],
                        "affected_controlled_revisions": ["DOC-REV-001"],
                    },
                )
                self.assertEqual(create_resp.status_code, 200, create_resp.text)
                request_id = create_resp.json()["request_id"]

            eval_app = self._build_app(current_user_id="eval-1", deps=deps)
            with TestClient(eval_app) as client:
                evaluate_resp = client.post(
                    f"/api/change-control/requests/{request_id}/evaluate",
                    json={"evaluation_summary": "Risk acceptable with plan controls"},
                )
                self.assertEqual(evaluate_resp.status_code, 200, evaluate_resp.text)
                self.assertEqual(evaluate_resp.json()["status"], "evaluated")

            owner_app = self._build_app(current_user_id="owner-1", deps=deps)
            with TestClient(owner_app) as client:
                plan_item_resp = client.post(
                    f"/api/change-control/requests/{request_id}/plan-items",
                    json={
                        "title": "Implement and verify change",
                        "assignee_user_id": "owner-1",
                        "due_date": "2026-04-18",
                    },
                )
                self.assertEqual(plan_item_resp.status_code, 200, plan_item_resp.text)
                plan_item_id = plan_item_resp.json()["plan_items"][0]["plan_item_id"]
                planned_resp = client.post(
                    f"/api/change-control/requests/{request_id}/plan",
                    json={"plan_summary": "Single controlled item"},
                )
                self.assertEqual(planned_resp.status_code, 200, planned_resp.text)
                self.assertEqual(planned_resp.json()["status"], "planned")
                start_resp = client.post(f"/api/change-control/requests/{request_id}/start-execution")
                self.assertEqual(start_resp.status_code, 200, start_resp.text)
                done_item_resp = client.patch(
                    f"/api/change-control/requests/{request_id}/plan-items/{plan_item_id}",
                    json={"status": "completed", "completion_note": "done"},
                )
                self.assertEqual(done_item_resp.status_code, 200, done_item_resp.text)
                complete_exec_resp = client.post(
                    f"/api/change-control/requests/{request_id}/complete-execution",
                    json={"execution_summary": "Execution complete"},
                )
                self.assertEqual(complete_exec_resp.status_code, 200, complete_exec_resp.text)
                self.assertEqual(complete_exec_resp.json()["status"], "pending_confirmation")

            qa_app = self._build_app(current_user_id="qa-1", deps=deps)
            with TestClient(qa_app) as client:
                qa_confirm_resp = client.post(
                    f"/api/change-control/requests/{request_id}/confirmations",
                    json={"department_code": "qa", "notes": "QA accepted"},
                )
                self.assertEqual(qa_confirm_resp.status_code, 200, qa_confirm_resp.text)
                self.assertEqual(qa_confirm_resp.json()["status"], "pending_confirmation")

            ops_app = self._build_app(current_user_id="ops-1", deps=deps)
            with TestClient(ops_app) as client:
                ops_confirm_resp = client.post(
                    f"/api/change-control/requests/{request_id}/confirmations",
                    json={"department_code": "ops", "notes": "OPS accepted"},
                )
                self.assertEqual(ops_confirm_resp.status_code, 200, ops_confirm_resp.text)
                self.assertEqual(ops_confirm_resp.json()["status"], "confirmed")

            owner_app = self._build_app(current_user_id="owner-1", deps=deps)
            with TestClient(owner_app) as client:
                close_resp = client.post(
                    f"/api/change-control/requests/{request_id}/close",
                    json={
                        "close_summary": "Closed with full traceability",
                        "close_outcome": "effective",
                        "ledger_writeback_ref": "LEDGER-2026-04-13-001",
                        "closed_controlled_revisions": ["DOC-REV-001", "DOC-REV-002"],
                    },
                )
                self.assertEqual(close_resp.status_code, 200, close_resp.text)
                payload = close_resp.json()
                self.assertEqual(payload["status"], "closed")
                self.assertEqual(payload["ledger_writeback_ref"], "LEDGER-2026-04-13-001")
                self.assertEqual(payload["closed_controlled_revisions"], ["DOC-REV-001", "DOC-REV-002"])
                self.assertIn("closed", [item["action"] for item in payload["actions"]])
        finally:
            cleanup_dir(td)

    def test_dispatch_reminders_writes_inbox_payload(self):
        td = make_temp_dir(prefix="ragflowauth_change_control_reminders")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "owner-1": _make_user(user_id="owner-1", role="sub_admin"),
                "eval-1": _make_user(user_id="eval-1", role="sub_admin"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/change-control/requests",
                    json={
                        "title": "Reminder path",
                        "reason": "Need due reminder",
                        "owner_user_id": "owner-1",
                        "evaluator_user_id": "eval-1",
                        "required_departments": [],
                        "affected_controlled_revisions": ["DOC-REV-010"],
                    },
                )
                request_id = create_resp.json()["request_id"]

            eval_app = self._build_app(current_user_id="eval-1", deps=deps)
            with TestClient(eval_app) as client:
                client.post(
                    f"/api/change-control/requests/{request_id}/evaluate",
                    json={"evaluation_summary": "ok"},
                )

            owner_app = self._build_app(current_user_id="owner-1", deps=deps)
            with TestClient(owner_app) as client:
                client.post(
                    f"/api/change-control/requests/{request_id}/plan-items",
                    json={
                        "title": "due item",
                        "assignee_user_id": "owner-1",
                        "due_date": "2026-04-14",
                    },
                )
                client.post(
                    f"/api/change-control/requests/{request_id}/plan",
                    json={"plan_summary": "ready"},
                )

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                dispatch_resp = client.post("/api/change-control/reminders/dispatch?window_days=30")
                self.assertEqual(dispatch_resp.status_code, 200, dispatch_resp.text)
                self.assertGreaterEqual(dispatch_resp.json()["count"], 1)

            inbox = deps.user_inbox_service.list_items(recipient_user_id="owner-1", unread_only=False, limit=20)
            self.assertGreaterEqual(inbox["count"], 1)
            self.assertEqual(inbox["items"][0]["event_type"], "change_control_due_soon")
        finally:
            cleanup_dir(td)

    def test_plan_requires_existing_items(self):
        td = make_temp_dir(prefix="ragflowauth_change_control_state_guard")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            users = {
                "admin-1": _make_user(user_id="admin-1", role="admin"),
                "owner-1": _make_user(user_id="owner-1", role="sub_admin"),
                "eval-1": _make_user(user_id="eval-1", role="sub_admin"),
            }
            deps = _Deps(db_path=db_path, users=users)

            admin_app = self._build_app(current_user_id="admin-1", deps=deps)
            with TestClient(admin_app) as client:
                create_resp = client.post(
                    "/api/change-control/requests",
                    json={
                        "title": "Plan guard",
                        "reason": "Need item before plan",
                        "owner_user_id": "owner-1",
                        "evaluator_user_id": "eval-1",
                        "required_departments": [],
                        "affected_controlled_revisions": ["DOC-REV-100"],
                    },
                )
                request_id = create_resp.json()["request_id"]

            eval_app = self._build_app(current_user_id="eval-1", deps=deps)
            with TestClient(eval_app) as client:
                client.post(
                    f"/api/change-control/requests/{request_id}/evaluate",
                    json={"evaluation_summary": "ok"},
                )

            owner_app = self._build_app(current_user_id="owner-1", deps=deps)
            with TestClient(owner_app) as client:
                plan_resp = client.post(
                    f"/api/change-control/requests/{request_id}/plan",
                    json={"plan_summary": "no items"},
                )
                self.assertEqual(plan_resp.status_code, 409, plan_resp.text)
                self.assertEqual(plan_resp.json()["detail"], "change_request_plan_items_required")
        finally:
            cleanup_dir(td)
