import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core import authz as authz_module
from backend.app.modules.org_directory.router import router as org_router
from backend.database.schema.ensure import ensure_schema
from backend.services.org_directory import OrgDirectoryStore, OrgStructureManager
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UserStore:
    def get_usernames_by_ids(self, user_ids):
        return {str(user_id): f"user-{user_id}" for user_id in user_ids}


class _Deps(SimpleNamespace):
    pass


def _override_admin_only() -> TokenPayload:
    return TokenPayload(sub="admin-1")


class TestOrgDirectoryApiUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_org_directory_api")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.manager = OrgStructureManager(store=OrgDirectoryStore(db_path=self.db_path))

        self.app = FastAPI()
        self.app.state.deps = _Deps(
            org_structure_manager=self.manager,
            user_store=_UserStore(),
        )
        self.app.include_router(org_router, prefix="/api")
        self.app.dependency_overrides[authz_module.admin_only] = _override_admin_only
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        cleanup_dir(self._tmp)

    @staticmethod
    def _flatten_tree(nodes):
        flattened = []
        stack = list(nodes)
        while stack:
            node = stack.pop(0)
            flattened.append(node)
            stack[0:0] = list(node.get("children") or [])
        return flattened

    def _post_excel_rebuild(self, *, filename: str | None = None, content: bytes | None = None):
        if filename is not None:
            return self.client.post(
                "/api/org/rebuild-from-excel",
                files={"excel_file": (filename, content or b"", "application/octet-stream")},
            )

        with open(self.manager.excel_path, "rb") as handle:
            return self.client.post(
                "/api/org/rebuild-from-excel",
                files={
                    "excel_file": (
                        self.manager.excel_path.name,
                        handle,
                        "application/vnd.ms-excel",
                    )
                },
            )

    def test_rebuild_tree_and_flat_department_api(self):
        rebuild_resp = self._post_excel_rebuild()
        self.assertEqual(rebuild_resp.status_code, 200, rebuild_resp.text)
        self.assertEqual(rebuild_resp.json()["company_count"], 21)
        self.assertEqual(rebuild_resp.json()["department_count"], 302)
        self.assertEqual(rebuild_resp.json()["employee_count"], 2027)
        self.assertEqual(rebuild_resp.json()["excel_path"], self.manager.excel_path.name)

        tree_resp = self.client.get("/api/org/tree")
        self.assertEqual(tree_resp.status_code, 200, tree_resp.text)
        tree = tree_resp.json()
        flat_tree = self._flatten_tree(tree)
        person_nodes = [item for item in flat_tree if item["node_type"] == "person"]
        self.assertEqual(len(tree), 21)
        self.assertTrue(all(item["node_type"] == "company" for item in tree))
        self.assertTrue(any(item["children"] for item in tree))
        self.assertEqual(len(person_nodes), 2027)
        self.assertTrue(any(item["department_id"] is None for item in person_nodes))
        self.assertTrue(any(item["department_id"] is not None for item in person_nodes))
        self.assertTrue(all("employee_user_id" in item for item in person_nodes))

        departments_resp = self.client.get("/api/org/departments")
        self.assertEqual(departments_resp.status_code, 200, departments_resp.text)
        departments = departments_resp.json()
        self.assertEqual(len(departments), 302)
        self.assertTrue(any(" / " in str(item.get("path_name") or "") for item in departments))
        self.assertTrue(all("company_id" in item for item in departments))

        audit_resp = self.client.get("/api/org/audit?entity_type=org_structure&action=rebuild&limit=10")
        self.assertEqual(audit_resp.status_code, 200, audit_resp.text)
        audit_rows = audit_resp.json()
        self.assertEqual(len(audit_rows), 1)
        self.assertEqual(audit_rows[0]["entity_type"], "org_structure")
        self.assertEqual(audit_rows[0]["action"], "rebuild")

    def test_rebuild_requires_supported_excel_upload(self):
        invalid_type_resp = self._post_excel_rebuild(filename="org.txt", content=b"not-excel")
        self.assertEqual(invalid_type_resp.status_code, 400, invalid_type_resp.text)
        self.assertEqual(invalid_type_resp.json()["detail"], "org_structure_excel_extension_invalid:.txt")

        missing_file_resp = self.client.post("/api/org/rebuild-from-excel")
        self.assertEqual(missing_file_resp.status_code, 422, missing_file_resp.text)

    def test_manual_company_department_crud_is_blocked(self):
        create_company_resp = self.client.post("/api/org/companies", json={"name": "New Company"})
        self.assertEqual(create_company_resp.status_code, 409, create_company_resp.text)
        self.assertEqual(create_company_resp.json()["detail"], "org_structure_managed_by_excel")

        update_company_resp = self.client.put("/api/org/companies/1", json={"name": "Updated Company"})
        self.assertEqual(update_company_resp.status_code, 409, update_company_resp.text)
        self.assertEqual(update_company_resp.json()["detail"], "org_structure_managed_by_excel")

        delete_company_resp = self.client.delete("/api/org/companies/1")
        self.assertEqual(delete_company_resp.status_code, 409, delete_company_resp.text)
        self.assertEqual(delete_company_resp.json()["detail"], "org_structure_managed_by_excel")

        create_department_resp = self.client.post("/api/org/departments", json={"name": "New Department"})
        self.assertEqual(create_department_resp.status_code, 409, create_department_resp.text)
        self.assertEqual(create_department_resp.json()["detail"], "org_structure_managed_by_excel")

        update_department_resp = self.client.put("/api/org/departments/1", json={"name": "Updated Department"})
        self.assertEqual(update_department_resp.status_code, 409, update_department_resp.text)
        self.assertEqual(update_department_resp.json()["detail"], "org_structure_managed_by_excel")

        delete_department_resp = self.client.delete("/api/org/departments/1")
        self.assertEqual(delete_department_resp.status_code, 409, delete_department_resp.text)
        self.assertEqual(delete_department_resp.json()["detail"], "org_structure_managed_by_excel")


if __name__ == "__main__":
    unittest.main()
