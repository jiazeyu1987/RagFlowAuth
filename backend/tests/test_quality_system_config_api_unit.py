import os
import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.audit.router import router as audit_router
from backend.app.modules.quality_system_config.router import router as quality_system_config_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.org_directory_store import OrgDirectoryStore, OrgStructureManager
from backend.services.users.store import UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self, *, db_path: str):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = UserStore(db_path=db_path)
        self.org_directory_store = OrgDirectoryStore(db_path=db_path)
        self.org_structure_manager = OrgStructureManager(store=self.org_directory_store)
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)
        self.permission_group_store = _PermissionGroupStore()


def _payload_override(user_id: str):
    def _override(_: Request) -> TokenPayload:
        return TokenPayload(sub=user_id)

    return _override


def _create_user(
    store: UserStore,
    *,
    username: str,
    role: str,
    status: str = "active",
    employee_user_id: str | None = None,
    full_name: str | None = None,
):
    return store.create_user(
        username=username,
        password="secret123",
        employee_user_id=employee_user_id,
        full_name=full_name,
        email=f"{username}@example.com",
        manager_user_id=None,
        company_id=None,
        department_id=None,
        role=role,
        group_id=None,
        status=status,
        max_login_sessions=3,
        idle_timeout_minutes=120,
        can_change_password=True,
        disable_login_enabled=False,
        disable_login_until_ms=None,
        electronic_signature_enabled=True,
        created_by="system",
        managed_kb_root_node_id=None,
    )


class TestQualitySystemConfigApiUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_quality_system_config")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.deps = _Deps(db_path=self.db_path)
        self.admin_user = _create_user(
            self.deps.user_store,
            username="admin1",
            role="admin",
            employee_user_id="admin-emp-1",
            full_name="Admin One",
        )
        self.active_bound_a = _create_user(
            self.deps.user_store,
            username="qa_user",
            role="viewer",
            employee_user_id="emp-qa-1",
            full_name="QA User",
        )
        self.active_bound_b = _create_user(
            self.deps.user_store,
            username="doc_user",
            role="viewer",
            employee_user_id="emp-doc-1",
            full_name="Doc User",
        )
        self.inactive_bound = _create_user(
            self.deps.user_store,
            username="inactive_user",
            role="viewer",
            status="inactive",
            employee_user_id="emp-inactive-1",
            full_name="Inactive User",
        )
        self.active_unbound = _create_user(
            self.deps.user_store,
            username="unbound_user",
            role="viewer",
            employee_user_id=None,
            full_name="Unbound User",
        )

        self.app = FastAPI()
        self.app.state.deps = self.deps
        self.app.include_router(quality_system_config_router, prefix="/api")
        self.app.include_router(audit_router, prefix="/api")
        self.app.dependency_overrides[auth_module.get_current_payload] = _payload_override(
            self.admin_user.user_id
        )

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_get_config_seeds_positions_and_file_categories(self):
        with TestClient(self.app) as client:
            response = client.get("/api/admin/quality-system-config")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertGreater(len(payload["positions"]), 0)
        self.assertGreater(len(payload["file_categories"]), 0)
        names = {item["name"] for item in payload["positions"]}
        self.assertIn("QA", names)
        self.assertIn("项目负责人", names)
        self.assertIn("编制部门负责人或授权代表", names)

    def test_search_users_only_returns_active_bound_users(self):
        with TestClient(self.app) as client:
            response = client.get("/api/admin/quality-system-config/users", params={"q": "emp-qa"})

        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["user_id"], self.active_bound_a.user_id)
        self.assertEqual(items[0]["employee_user_id"], "emp-qa-1")

    def test_update_assignments_and_file_categories_write_audit_events(self):
        with TestClient(self.app) as client:
            config_resp = client.get("/api/admin/quality-system-config")
            self.assertEqual(config_resp.status_code, 200, config_resp.text)
            config_payload = config_resp.json()

            qa_position = next(item for item in config_payload["positions"] if item["name"] == "QA")
            update_resp = client.put(
                f"/api/admin/quality-system-config/positions/{qa_position['id']}/assignments",
                json={
                    "user_ids": [self.active_bound_a.user_id, self.active_bound_b.user_id],
                    "change_reason": "Assign QA owners",
                },
            )
            self.assertEqual(update_resp.status_code, 200, update_resp.text)
            updated_position = update_resp.json()
            self.assertEqual(
                [item["user_id"] for item in updated_position["assigned_users"]],
                [self.active_bound_a.user_id, self.active_bound_b.user_id],
            )

            create_category_resp = client.post(
                "/api/admin/quality-system-config/file-categories",
                json={
                    "name": "新增文件小类",
                    "change_reason": "Add custom category",
                },
            )
            self.assertEqual(create_category_resp.status_code, 200, create_category_resp.text)
            category = create_category_resp.json()

            deactivate_resp = client.post(
                f"/api/admin/quality-system-config/file-categories/{category['id']}/deactivate",
                json={"change_reason": "Retire custom category"},
            )
            self.assertEqual(deactivate_resp.status_code, 200, deactivate_resp.text)
            self.assertFalse(deactivate_resp.json()["is_active"])

            refreshed = client.get("/api/admin/quality-system-config")
            self.assertEqual(refreshed.status_code, 200, refreshed.text)
            refreshed_categories = {item["name"] for item in refreshed.json()["file_categories"]}
            self.assertNotIn("新增文件小类", refreshed_categories)

            audit_resp = client.get("/api/audit/events")
            self.assertEqual(audit_resp.status_code, 200, audit_resp.text)
            audit_items = audit_resp.json()["items"]

        assignment_event = next(
            item for item in audit_items if item["action"] == "quality_system_position_assignments_update"
        )
        self.assertEqual(assignment_event["source"], "quality_system_config")
        self.assertEqual(assignment_event["resource_type"], "quality_system_position_assignment")
        self.assertEqual(assignment_event["resource_id"], "QA")
        self.assertEqual(assignment_event["reason"], "Assign QA owners")
        self.assertEqual(len(assignment_event["after"]["assigned_users"]), 2)

        create_event = next(
            item for item in audit_items if item["action"] == "quality_system_file_category_create"
        )
        self.assertEqual(create_event["resource_id"], "新增文件小类")
        self.assertEqual(create_event["reason"], "Add custom category")

        deactivate_event = next(
            item for item in audit_items if item["action"] == "quality_system_file_category_deactivate"
        )
        self.assertEqual(deactivate_event["resource_id"], "新增文件小类")
        self.assertEqual(deactivate_event["reason"], "Retire custom category")


if __name__ == "__main__":
    unittest.main()
