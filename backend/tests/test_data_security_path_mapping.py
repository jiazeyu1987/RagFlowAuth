import os
import unittest


class TestDataSecurityPathMapping(unittest.TestCase):
    def setUp(self):
        self._old_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_container_path_to_host_str_fallback_uses_env(self):
        from backend.services.data_security.docker_utils import container_path_to_host_str

        os.environ["RAGFLOWAUTH_HOST_BACKUPS_DIR"] = "/host/backups"
        os.environ["RAGFLOWAUTH_HOST_DATA_DIR"] = "/host/data"
        os.environ["RAGFLOWAUTH_HOST_UPLOADS_DIR"] = "/host/uploads"

        self.assertEqual(
            container_path_to_host_str("/app/data/backups/migration_pack_x/volumes/a.tar.gz"),
            "/host/backups/migration_pack_x/volumes/a.tar.gz",
        )
        self.assertEqual(
            container_path_to_host_str("/app/data/auth.db"),
            "/host/data/auth.db",
        )
        self.assertEqual(
            container_path_to_host_str("/app/uploads/file.bin"),
            "/host/uploads/file.bin",
        )

