import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.system_feature_flag_store import (
    FLAG_EGRESS_POLICY_ENABLED,
    FLAG_PAPER_PLAG_ENABLED,
    FLAG_RESEARCH_UI_LAYOUT_ENABLED,
    SystemFeatureFlagStore,
)
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestSystemFeatureFlagStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_feature_flag_store")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.store = SystemFeatureFlagStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_list_flags_returns_default_enabled_flags(self):
        payload = self.store.list_flags()
        self.assertTrue(bool(payload.get(FLAG_PAPER_PLAG_ENABLED)))
        self.assertTrue(bool(payload.get(FLAG_EGRESS_POLICY_ENABLED)))
        self.assertTrue(bool(payload.get(FLAG_RESEARCH_UI_LAYOUT_ENABLED)))

    def test_update_flags_accepts_bool_and_string_values(self):
        payload = self.store.update_flags(
            {
                FLAG_PAPER_PLAG_ENABLED: False,
                FLAG_EGRESS_POLICY_ENABLED: "0",
                FLAG_RESEARCH_UI_LAYOUT_ENABLED: "true",
            },
            actor_user_id="admin_u1",
        )
        self.assertFalse(bool(payload.get(FLAG_PAPER_PLAG_ENABLED)))
        self.assertFalse(bool(payload.get(FLAG_EGRESS_POLICY_ENABLED)))
        self.assertTrue(bool(payload.get(FLAG_RESEARCH_UI_LAYOUT_ENABLED)))

    def test_rollback_disable_all_turns_three_flags_off(self):
        payload = self.store.rollback_disable_all(actor_user_id="admin_u1")
        self.assertFalse(bool(payload.get(FLAG_PAPER_PLAG_ENABLED)))
        self.assertFalse(bool(payload.get(FLAG_EGRESS_POLICY_ENABLED)))
        self.assertFalse(bool(payload.get(FLAG_RESEARCH_UI_LAYOUT_ENABLED)))

    def test_update_flags_rejects_unknown_flag(self):
        with self.assertRaises(ValueError):
            self.store.update_flags({"unknown_feature": True}, actor_user_id="admin_u1")


if __name__ == "__main__":
    unittest.main()
