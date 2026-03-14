import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.feature_visibility_store import (
    FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE,
    FLAG_API_AUDIT_EVENTS_VISIBLE,
    FLAG_API_DIAGNOSTICS_VISIBLE,
    FLAG_PAGE_DATA_SECURITY_TEST_VISIBLE,
    FLAG_PAGE_LOGS_VISIBLE,
    FLAG_TOOL_DRUG_ADMIN_VISIBLE,
    FLAG_TOOL_NAS_VISIBLE,
    FLAG_TOOL_NMPA_VISIBLE,
    FLAG_TOOL_NHSA_VISIBLE,
    FLAG_TOOL_SH_TAX_VISIBLE,
    FeatureVisibilityStore,
)
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestFeatureVisibilityStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_feature_visibility_store")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = FeatureVisibilityStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_list_flags_defaults_are_visible(self):
        payload = self.store.list_flags()
        self.assertTrue(bool(payload.get(FLAG_TOOL_NHSA_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_TOOL_SH_TAX_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_TOOL_DRUG_ADMIN_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_TOOL_NMPA_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_TOOL_NAS_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_PAGE_DATA_SECURITY_TEST_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_PAGE_LOGS_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_API_AUDIT_EVENTS_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_API_DIAGNOSTICS_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_API_ADMIN_FEATURE_FLAGS_VISIBLE)))

    def test_update_flags_supports_boolean_and_string(self):
        payload = self.store.update_flags(
            {
                FLAG_TOOL_NHSA_VISIBLE: False,
                FLAG_TOOL_SH_TAX_VISIBLE: "0",
                FLAG_TOOL_DRUG_ADMIN_VISIBLE: "false",
                FLAG_API_DIAGNOSTICS_VISIBLE: True,
            },
            actor_user_id="builtin_super_admin",
        )
        self.assertFalse(bool(payload.get(FLAG_TOOL_NHSA_VISIBLE)))
        self.assertFalse(bool(payload.get(FLAG_TOOL_SH_TAX_VISIBLE)))
        self.assertFalse(bool(payload.get(FLAG_TOOL_DRUG_ADMIN_VISIBLE)))
        self.assertTrue(bool(payload.get(FLAG_API_DIAGNOSTICS_VISIBLE)))

    def test_update_flags_rejects_unknown_key(self):
        with self.assertRaises(ValueError):
            self.store.update_flags({"unknown_visibility_key": True}, actor_user_id="builtin_super_admin")


if __name__ == "__main__":
    unittest.main()
