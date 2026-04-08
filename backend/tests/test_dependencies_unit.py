import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI

from backend.app.dependencies import create_dependencies, get_tenant_dependencies, initialize_application_dependencies


class TestDependenciesUnit(unittest.TestCase):
    def test_operation_approval_reuses_shared_signature_service_when_control_db_is_separate(self):
        with tempfile.TemporaryDirectory(prefix="ragflowauth_deps_") as temp_dir:
            root = Path(temp_dir)
            main_db = root / "main_auth.db"
            approval_db = root / "approval_auth.db"

            deps = create_dependencies(
                db_path=str(main_db),
                operation_approval_control_db_path=str(approval_db),
            )

            self.assertIsNotNone(deps.electronic_signature_service)
            self.assertIsNotNone(deps.operation_approval_service)
            self.assertIs(
                deps.operation_approval_service._signature_service,
                deps.electronic_signature_service,
            )

    def test_initialize_application_dependencies_sets_global_state_and_tenant_cache(self):
        with tempfile.TemporaryDirectory(prefix="ragflowauth_deps_app_") as temp_dir:
            root = Path(temp_dir)
            global_db = root / "global" / "auth.db"
            app = FastAPI()

            with patch("backend.app.dependencies.resolve_auth_db_path", return_value=global_db):
                deps = initialize_application_dependencies(app)

            self.assertIs(app.state.deps, deps)
            self.assertEqual(app.state.base_auth_db_path, str(global_db))
            self.assertEqual(app.state.tenant_deps_cache, {})

            tenant_deps_first = get_tenant_dependencies(app, company_id=7)
            tenant_deps_second = get_tenant_dependencies(app, company_id="7")

            self.assertIs(tenant_deps_first, tenant_deps_second)
            self.assertIs(app.state.tenant_deps_cache[7], tenant_deps_first)

            tenant_kb_path = str(tenant_deps_first.kb_store.db_path).replace("\\", "/")
            approval_control_path = str(tenant_deps_first.operation_approval_service._store.db_path).replace("\\", "/")

            self.assertIn("/tenants/company_7/auth.db", tenant_kb_path)
            self.assertTrue(approval_control_path.endswith("/global/auth.db"))


if __name__ == "__main__":
    unittest.main()
