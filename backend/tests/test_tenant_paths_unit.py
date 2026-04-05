import unittest
from pathlib import Path

from backend.database.paths import resolve_auth_db_path
from backend.database.tenant_paths import (
    resolve_tenant_auth_db_path,
    resolve_tenant_db_root,
)


class TenantPathsTests(unittest.TestCase):
    def test_default_auth_db_keeps_legacy_tenant_root(self):
        base_db = resolve_auth_db_path(Path("data") / "auth.db")
        root = resolve_tenant_db_root(base_db)
        self.assertEqual(root, base_db.parent / "tenants")
        tenant_db = resolve_tenant_auth_db_path(19, base_db)
        self.assertEqual(tenant_db, base_db.parent / "tenants" / "company_19" / "auth.db")

    def test_non_default_auth_db_uses_isolated_tenant_root(self):
        worker_a_db = resolve_auth_db_path(Path("data") / "e2e" / "worker01_doc_auth.db")
        worker_b_db = resolve_auth_db_path(Path("data") / "e2e" / "worker02_doc_auth.db")
        worker_a_root = resolve_tenant_db_root(worker_a_db)
        worker_b_root = resolve_tenant_db_root(worker_b_db)
        self.assertEqual(worker_a_root, worker_a_db.parent / "tenants__worker01_doc_auth")
        self.assertEqual(worker_b_root, worker_b_db.parent / "tenants__worker02_doc_auth")
        self.assertNotEqual(worker_a_root, worker_b_root)

        worker_a_tenant = resolve_tenant_auth_db_path(19, worker_a_db)
        worker_b_tenant = resolve_tenant_auth_db_path(19, worker_b_db)
        self.assertEqual(
            worker_a_tenant,
            worker_a_db.parent / "tenants__worker01_doc_auth" / "company_19" / "auth.db",
        )
        self.assertEqual(
            worker_b_tenant,
            worker_b_db.parent / "tenants__worker02_doc_auth" / "company_19" / "auth.db",
        )
        self.assertNotEqual(worker_a_tenant, worker_b_tenant)


if __name__ == "__main__":
    unittest.main()
