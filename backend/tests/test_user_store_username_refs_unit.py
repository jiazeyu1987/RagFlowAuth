import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.users.store import UserStore


class TestUserStoreUsernameRefsUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = UserStore(db_path=self.db_path)
        self.user = self.store.create_user(username="14", password="14", email=None)

    def tearDown(self):
        self._tmp.cleanup()

    def test_get_usernames_by_ids_supports_user_id_and_username_refs(self):
        result = self.store.get_usernames_by_ids({self.user.user_id, "14"})
        self.assertEqual(result.get(self.user.user_id), "14")
        self.assertEqual(result.get("14"), "14")


if __name__ == "__main__":
    unittest.main()
