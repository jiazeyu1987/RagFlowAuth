from __future__ import annotations

from pathlib import Path
import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.core.auth import get_deps
from backend.app.dependencies import AppDependencies, create_dependencies, get_tenant_dependencies
from backend.core.security import auth
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
        total_a, _ = deps_a.audit_log_store.list_events()
        total_b, _ = deps_b.audit_log_store.list_events()
        self.assertEqual(total_a, 1)
        self.assertEqual(total_b, 1)

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


if __name__ == "__main__":
    unittest.main()
