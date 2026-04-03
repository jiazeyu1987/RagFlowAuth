import json
import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.config_change_log_store import ConfigChangeLogStore
from backend.services.data_security import DataSecurityStore
from backend.services.upload_settings_store import UploadSettingsStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestConfigChangeLogUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_config_log")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.log_store = ConfigChangeLogStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_upload_settings_update_records_before_after_and_reason(self):
        store = UploadSettingsStore(db_path=self.db_path)

        updated = store.update_allowed_extensions(
            ["PDF", ".dwg"],
            changed_by="admin-1",
            change_reason="Allow CAD uploads",
        )

        rows = self.log_store.list_logs(config_domain="upload_allowed_extensions")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].changed_by, "admin-1")
        self.assertEqual(rows[0].change_reason, "Allow CAD uploads")
        self.assertEqual(json.loads(rows[0].after_json)["allowed_extensions"], updated.allowed_extensions)
        self.assertIn(".pdf", json.loads(rows[0].before_json)["allowed_extensions"])
        self.assertIn(".dwg", json.loads(rows[0].after_json)["allowed_extensions"])

    def test_data_security_update_records_before_after_and_reason(self):
        store = DataSecurityStore(db_path=self.db_path)

        updated = store.update_settings(
            {"target_local_dir": "/backup/company_a", "backup_retention_max": 45},
            changed_by="admin-2",
            change_reason="Adjust retention and target path",
        )

        rows = self.log_store.list_logs(config_domain="data_security_settings")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].changed_by, "admin-2")
        self.assertEqual(rows[0].change_reason, "Adjust retention and target path")
        before = json.loads(rows[0].before_json)
        after = json.loads(rows[0].after_json)
        self.assertNotEqual(before["target_local_dir"], after["target_local_dir"])
        self.assertEqual(after["target_local_dir"], updated.target_local_dir)
        self.assertEqual(after["backup_retention_max"], 45)


if __name__ == "__main__":
    unittest.main()
