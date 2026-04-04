from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.dependencies import create_dependencies, get_tenant_dependencies
from backend.app.modules.users.router import router as users_router
from backend.core.security import auth
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestSubAdminUserVisibilityGlobalStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_sub_admin_users")
        self.global_db = self._tmp / "global" / "auth.db"

        self.app = FastAPI()
        self.app.state.base_auth_db_path = str(self.global_db)
        self.app.state.tenant_deps_cache = {}
        self.app.state.deps = create_dependencies(
            db_path=str(self.global_db),
            operation_approval_execution_deps_resolver=lambda company_id: get_tenant_dependencies(
                self.app,
                company_id=company_id,
            ),
        )
        self.app.include_router(users_router, prefix="/api/users")

        self.global_deps = self.app.state.deps
        self.tenant_deps = get_tenant_dependencies(self.app, company_id=1)

        root = self.tenant_deps.knowledge_directory_store.create_node("Root", None, created_by="admin")
        self.root_node_id = str(root["node_id"])

        self.sub_admin = self.global_deps.user_store.create_user(
            username="wangxin",
            password="Pass1234",
            company_id=1,
            role="sub_admin",
            managed_kb_root_node_id=self.root_node_id,
        )
        self.other_sub_admin = self.global_deps.user_store.create_user(
            username="other_sub",
            password="Pass1234",
            company_id=1,
            role="sub_admin",
            managed_kb_root_node_id=self.root_node_id,
        )
        self.owned_user_a = self.global_deps.user_store.create_user(
            username="viewer_a",
            password="Pass1234",
            company_id=1,
            role="viewer",
            manager_user_id=self.sub_admin.user_id,
        )
        self.owned_user_b = self.global_deps.user_store.create_user(
            username="viewer_b",
            password="Pass1234",
            company_id=1,
            role="viewer",
            manager_user_id=self.sub_admin.user_id,
        )
        self.other_user_same_company = self.global_deps.user_store.create_user(
            username="viewer_other",
            password="Pass1234",
            company_id=1,
            role="viewer",
            manager_user_id=self.other_sub_admin.user_id,
        )
        self.other_company_user = self.global_deps.user_store.create_user(
            username="viewer_other_company",
            password="Pass1234",
            company_id=2,
            role="viewer",
            manager_user_id=self.sub_admin.user_id,
        )

        self.group_id = self.tenant_deps.permission_group_store.create_group(
            group_name="owned-group",
            created_by=self.sub_admin.user_id,
            accessible_kb_nodes=[self.root_node_id],
            accessible_kbs=[],
            accessible_chats=[],
        )
        if not self.group_id:
            raise AssertionError("permission_group_create_failed")

        self.session_id = "sid-sub-admin-users"
        self.global_deps.auth_session_store.create_session(
            session_id=self.session_id,
            user_id=self.sub_admin.user_id,
            refresh_jti=None,
            expires_at=None,
        )
        self.token = auth.create_access_token(
            uid=self.sub_admin.user_id,
            scopes=[],
            data={"sid": self.session_id, "cid": 1},
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_sub_admin_lists_owned_users_from_global_store_when_tenant_store_is_empty(self):
        self.assertIsNone(self.tenant_deps.user_store.get_by_user_id(self.owned_user_a.user_id))
        self.assertEqual(self.tenant_deps.user_store.list_users(limit=10), [])

        with TestClient(self.app) as client:
            response = client.get("/api/users", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        usernames = [item["username"] for item in response.json()]
        self.assertCountEqual(usernames, ["viewer_a", "viewer_b"])

    def test_sub_admin_can_assign_group_to_owned_user_without_tenant_user_mirror(self):
        self.assertIsNone(self.tenant_deps.user_store.get_by_user_id(self.owned_user_a.user_id))

        with TestClient(self.app) as client:
            response = client.put(
                f"/api/users/{self.owned_user_a.user_id}",
                headers=self.headers,
                json={"group_ids": [self.group_id]},
            )

        self.assertEqual(response.status_code, 200)
        updated_user = self.global_deps.user_store.get_by_user_id(self.owned_user_a.user_id)
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.group_ids, [self.group_id])


if __name__ == "__main__":
    unittest.main()
