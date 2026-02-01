import os
import unittest
from unittest import mock


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

    def test_docker_save_images_uses_container_path_not_host_path(self):
        from pathlib import Path

        from backend.services.data_security import docker_utils

        calls = []

        def fake_run_cmd(argv, cwd=None, **_kwargs):
            calls.append(list(argv))
            return 0, ""

        # Make file existence check pass without touching filesystem.
        with mock.patch.object(docker_utils, "run_cmd_live", side_effect=fake_run_cmd), mock.patch.object(
            docker_utils, "ensure_dir", return_value=None
        ), mock.patch.object(docker_utils.os.path, "exists", return_value=True), mock.patch.object(
            docker_utils.os.path, "getsize", return_value=123
        ):
            ok, err = docker_utils.docker_save_images(["a:b"], Path("/app/data/backups/migration_pack_x/images.tar"))

        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertTrue(calls)
        # -o must use container path (NOT translated to /opt/...)
        self.assertIn("-o", calls[0])
        out_path = calls[0][calls[0].index("-o") + 1]
        self.assertEqual(out_path, "/app/data/backups/migration_pack_x/images.tar")
