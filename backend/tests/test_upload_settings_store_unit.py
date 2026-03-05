import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.upload_settings_store import UploadSettingsStore


class TestUploadSettingsStoreUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = UploadSettingsStore(db_path=self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_get_returns_seeded_extensions(self):
        settings_obj = self.store.get()
        self.assertIn(".pdf", settings_obj.allowed_extensions)
        self.assertIn(".png", settings_obj.allowed_extensions)

    def test_update_normalizes_extensions(self):
        settings_obj = self.store.update_allowed_extensions(["PDF", ".txt", " jpg ", ".PDF"])
        self.assertEqual(settings_obj.allowed_extensions, [".jpg", ".pdf", ".txt"])

    def test_add_allowed_extension_if_missing(self):
        settings_obj = self.store.add_allowed_extension_if_missing(".ppt")
        self.assertIn(".ppt", settings_obj.allowed_extensions)
        again = self.store.add_allowed_extension_if_missing("ppt")
        self.assertEqual(settings_obj.allowed_extensions, again.allowed_extensions)


if __name__ == "__main__":
    unittest.main()
