from __future__ import annotations

from pathlib import Path
import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.core.auth import get_deps
from backend.app.dependencies import AppDependencies, create_dependencies, get_tenant_dependencies
from backend.core.security import auth
from backend.services.inbox_store import UserInboxStore
from backend.services.operation_approval import OperationApprovalStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestTenantDbIsolationUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_tenant_iso")
        self.global_db = self._tmp / "global" / "auth.db"
        self.global_deps = create_dependencies(db_path=str(self.global_db))

        self.app = FastAPI()
        self.app.state.deps = self.global_deps
        self.app.state.base_auth_db_path = str(self.global_db)
        self.app.state.tenant_deps_cache = {}

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_company_scoped_stores_are_isolated(self):
        deps_a = get_tenant_dependencies(self.app, company_id=1)
        deps_b = get_tenant_dependencies(self.app, company_id=2)

        user_a = deps_a.user_store.create_user(username="tenant_a", password="Pass1234", company_id=1, role="admin")
        user_b = deps_b.user_store.create_user(username="tenant_b", password="Pass1234", company_id=2, role="admin")

        file_a = Path(self._tmp) / "tenant_a.txt"
        file_b = Path(self._tmp) / "tenant_b.txt"
        file_a.write_text("a", encoding="utf-8")
        file_b.write_text("b", encoding="utf-8")

        doc_a = deps_a.kb_store.create_document(
            filename="a.txt",
            file_path=str(file_a),
            file_size=1,
            mime_type="text/plain",
            uploaded_by=user_a.user_id,
        )
        doc_b = deps_b.kb_store.create_document(
            filename="b.txt",
            file_path=str(file_b),
            file_size=1,
            mime_type="text/plain",
            uploaded_by=user_b.user_id,
        )

        self.assertEqual(deps_a.kb_store.count_documents(), 1)
        self.assertEqual(deps_b.kb_store.count_documents(), 1)
        self.assertIsNotNone(deps_a.kb_store.get_document(doc_a.doc_id))
        self.assertIsNotNone(deps_b.kb_store.get_document(doc_b.doc_id))
        self.assertIsNone(deps_a.kb_store.get_document(doc_b.doc_id))
        self.assertIsNone(deps_b.kb_store.get_document(doc_a.doc_id))

        deps_a.audit_log_store.log_event(action="tenant_a_event", actor=user_a.user_id, company_id=1, source="knowledge")
        deps_b.audit_log_store.log_event(action="tenant_b_event", actor=user_b.user_id, company_id=2, source="knowledge")
        total_a, rows_a = deps_a.audit_log_store.list_events()
        total_b, rows_b = deps_b.audit_log_store.list_events()
        actions_a = {row.action for row in rows_a}
        actions_b = {row.action for row in rows_b}
        self.assertGreaterEqual(total_a, 2)
        self.assertGreaterEqual(total_b, 2)
        self.assertIn("tenant_a_event", actions_a)
        self.assertIn("tenant_b_event", actions_b)
        self.assertNotIn("tenant_b_event", actions_a)
        self.assertNotIn("tenant_a_event", actions_b)

        deps_a.data_security_store.update_settings({"target_local_dir": "/backup/company_a"})
        deps_b.data_security_store.update_settings({"target_local_dir": "/backup/company_b"})
        settings_a = deps_a.data_security_store.get_settings()
        settings_b = deps_b.data_security_store.get_settings()
        self.assertEqual(settings_a.target_local_dir, "/backup/company_a")
        self.assertEqual(settings_b.target_local_dir, "/backup/company_b")

        path_a = str(deps_a.kb_store.db_path).replace("\\", "/")
        path_b = str(deps_b.kb_store.db_path).replace("\\", "/")
        self.assertNotEqual(path_a, path_b)
        self.assertIn("/tenants/company_1/auth.db", path_a)
        self.assertIn("/tenants/company_2/auth.db", path_b)

    def test_dependency_router_uses_company_claim(self):
        @self.app.get("/_tenant-db")
        async def _tenant_db(deps: AppDependencies = Depends(get_deps)):
            return {"db_path": str(deps.kb_store.db_path)}

        user_a = self.global_deps.user_store.create_user(
            username="global_company_a",
            password="Pass1234",
            company_id=1,
            role="admin",
        )
        user_b = self.global_deps.user_store.create_user(
            username="global_company_b",
            password="Pass1234",
            company_id=2,
            role="admin",
        )

        token_a = auth.create_access_token(uid=user_a.user_id, scopes=[], data={"sid": "s-a", "cid": 1})
        token_b_no_cid = auth.create_access_token(uid=user_b.user_id, scopes=[], data={"sid": "s-b"})

        with TestClient(self.app) as client:
            resp_global = client.get("/_tenant-db")
            self.assertEqual(resp_global.status_code, 200)
            global_path = str(resp_global.json()["db_path"]).replace("\\", "/")
            self.assertTrue(global_path.endswith("/global/auth.db"))

            resp_a = client.get("/_tenant-db", headers={"Authorization": f"Bearer {token_a}"})
            self.assertEqual(resp_a.status_code, 200)
            tenant_a_path = str(resp_a.json()["db_path"]).replace("\\", "/")
            self.assertIn("/tenants/company_1/auth.db", tenant_a_path)

            resp_b = client.get("/_tenant-db", headers={"Authorization": f"Bearer {token_b_no_cid}"})
            self.assertEqual(resp_b.status_code, 200)
            tenant_b_path = str(resp_b.json()["db_path"]).replace("\\", "/")
            self.assertIn("/tenants/company_2/auth.db", tenant_b_path)

    def test_tenant_operation_approval_uses_global_control_plane(self):
        approver = self.global_deps.user_store.create_user(
            username="tenant_approver",
            password="Pass1234",
            company_id=1,
            role="reviewer",
        )
        tenant_deps = get_tenant_dependencies(self.app, company_id=1)

        tenant_deps.operation_approval_service.upsert_workflow(
            operation_type="knowledge_file_upload",
            name="Tenant Upload Flow",
            steps=[
                {
                    "step_name": "Step 1",
                    "members": [{"member_type": "user", "member_ref": approver.user_id}],
                }
            ],
        )

        global_workflow = OperationApprovalStore(db_path=str(self.global_db)).get_workflow("knowledge_file_upload")
        tenant_workflow = OperationApprovalStore(db_path=str(tenant_deps.kb_store.db_path)).get_workflow(
            "knowledge_file_upload"
        )

        self.assertIsNotNone(global_workflow)
        self.assertEqual(global_workflow["name"], "Tenant Upload Flow")
        self.assertIsNone(tenant_workflow)
        control_db_path = str(tenant_deps.operation_approval_service._store.db_path).replace("\\", "/")
        tenant_kb_db_path = str(tenant_deps.kb_store.db_path).replace("\\", "/")
        self.assertTrue(control_db_path.endswith("/global/auth.db"))
        self.assertIn("/tenants/company_1/auth.db", tenant_kb_db_path)

    def test_tenant_inbox_uses_global_control_plane(self):
        recipient = self.global_deps.user_store.create_user(
            username="tenant_inbox_user",
            password="Pass1234",
            company_id=1,
            role="viewer",
        )
        tenant_deps = get_tenant_dependencies(self.app, company_id=1)

        tenant_deps.user_inbox_service.notify_users(
            recipients=[{"user_id": recipient.user_id, "username": recipient.username}],
            title="审批待处理",
            body="请处理审批",
            event_type="operation_approval_todo",
            link_path="/approvals?request_id=req-1",
            payload={"request_id": "req-1"},
        )

        global_inbox_store = UserInboxStore(db_path=str(self.global_db))
        tenant_inbox_store = UserInboxStore(db_path=str(tenant_deps.kb_store.db_path))
        global_items = global_inbox_store.list_items(recipient_user_id=recipient.user_id, limit=20)
        tenant_items = tenant_inbox_store.list_items(recipient_user_id=recipient.user_id, limit=20)

        self.assertEqual(len(global_items), 1)
        self.assertEqual(global_items[0]["title"], "审批待处理")
        self.assertEqual(len(tenant_items), 0)
        inbox_db_path = str(tenant_deps.user_inbox_store.db_path).replace("\\", "/")
        self.assertTrue(inbox_db_path.endswith("/global/auth.db"))

    def test_tenant_operation_approval_notifications_use_tenant_notification_manager(self):
        tenant_deps = get_tenant_dependencies(self.app, company_id=1)

        self.assertIsNotNone(tenant_deps.notification_manager)
        self.assertIsNotNone(tenant_deps.operation_approval_service._notification_service)
        self.assertIs(
            tenant_deps.operation_approval_service._notification_service,
            tenant_deps.notification_manager,
        )

        notification_db_path = str(tenant_deps.notification_manager._store.db_path).replace("\\", "/")
        operation_notification_db_path = str(
            tenant_deps.operation_approval_service._notification_service._store.db_path
        ).replace("\\", "/")
        self.assertIn("/tenants/company_1/auth.db", notification_db_path)
        self.assertEqual(operation_notification_db_path, notification_db_path)

        channel_types = {
            str(item.get("channel_type") or "").strip().lower()
            for item in tenant_deps.notification_manager.list_channels(enabled_only=False)
        }
        self.assertIn("in_app", channel_types)


if __name__ == "__main__":
    unittest.main()
