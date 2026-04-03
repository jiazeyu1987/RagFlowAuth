from __future__ import annotations

import unittest

from backend.services.users.store import UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir
from backend.database.schema.ensure import ensure_schema


class UserStoreFullNameMappingUnitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_user_store_mapping")
        self.db_path = str(self._tmp / "auth.db")
        ensure_schema(self.db_path)
        self.store = UserStore(db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_getters_read_full_name_from_full_name_column(self):
        created = self.store.create_user(
            username="wangxin",
            password="Secret123!",
            full_name="王歆",
            created_by="6567f115-49f7-49a3-86cf-2282ae823975",
            role="sub_admin",
            status="active",
        )

        by_username = self.store.get_by_username("wangxin")
        by_user_id = self.store.get_by_user_id(created.user_id)
        listed = self.store.list_users(limit=20)

        self.assertEqual("王歆", by_username.full_name)
        self.assertEqual("6567f115-49f7-49a3-86cf-2282ae823975", by_username.created_by)
        self.assertEqual("王歆", by_user_id.full_name)
        self.assertEqual("王歆", listed[0].full_name)


if __name__ == "__main__":
    unittest.main()
