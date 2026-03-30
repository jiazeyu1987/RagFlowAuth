import os
import tempfile
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.users.store import UserStore


class TestUserStoreFullNameUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self.db_path)
        self.store = UserStore(db_path=self.db_path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_create_update_and_query_by_full_name(self):
        user = self.store.create_user(
            username="alice",
            password="Pass1234",
            full_name="Alice Zhang",
            email="alice@example.com",
        )
        self.assertEqual(user.full_name, "Alice Zhang")

        fetched = self.store.get_by_username("alice")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.full_name, "Alice Zhang")

        updated = self.store.update_user(user.user_id, full_name="Alice Z")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.full_name, "Alice Z")

        rows = self.store.list_users(q="Alice Z", limit=20)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].username, "alice")


if __name__ == "__main__":
    unittest.main()
