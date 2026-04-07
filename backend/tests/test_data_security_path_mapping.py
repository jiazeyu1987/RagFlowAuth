import unittest
from unittest import mock
from pathlib import Path


class TestDataSecurityPathMapping(unittest.TestCase):
    def test_resolve_backend_helper_image_fails_fast_when_backend_container_missing(self):
        from backend.services.data_security import docker_utils

        with mock.patch.object(docker_utils, "run_cmd", return_value=(0, "")):
            with self.assertRaisesRegex(
                RuntimeError,
                "backup_worker_image_not_found:container=ragflowauth-backend",
            ):
                docker_utils.resolve_backend_helper_image()

    def test_resolve_backend_helper_image_uses_compose_project_image_on_host_runtime(self):
        from backend.services.data_security import docker_utils

        def fake_run_cmd(argv, cwd=None, **_kwargs):
            if argv[:4] == ["docker", "ps", "--filter", "name=ragflowauth-backend"]:
                return 0, ""
            if argv[:6] == [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=com.docker.compose.project=docker",
                "--format",
            ]:
                return 0, "mysql:8.0.39\ninfiniflow/ragflow:v0.22.1\n"
            if argv[:6] == ["docker", "compose", "-f", str(Path(r"D:\RagFlow\ragflow\docker\docker-compose.yml")), "config", "--images"]:
                return 0, "elasticsearch:8.11.3\ninfiniflow/ragflow:v0.22.1\n"
            if argv[:3] == ["docker", "image", "inspect"]:
                self.assertEqual(argv[3], "infiniflow/ragflow:v0.22.1")
                return 0, ""
            self.fail(f"unexpected call: {argv!r}")

        compose = Path(r"D:\RagFlow\ragflow\docker\docker-compose.yml")
        with mock.patch.object(Path, "exists", return_value=True), mock.patch.object(
            docker_utils, "run_cmd", side_effect=fake_run_cmd
        ):
            image = docker_utils.resolve_backend_helper_image(compose_file=compose, project_name="docker")

        self.assertEqual(image, "infiniflow/ragflow:v0.22.1")

    def test_docker_tar_volume_uses_resolved_backend_helper_image(self):
        from backend.services.data_security import docker_utils

        calls = []

        def fake_run_cmd_live(argv, **_kwargs):
            calls.append(list(argv))
            return 0, ""

        with mock.patch.object(
            docker_utils,
            "container_path_to_host_str",
            return_value="/host/backups",
        ), mock.patch.object(
            docker_utils,
            "resolve_backend_helper_image",
            return_value="backend-helper:test",
        ), mock.patch.object(
            docker_utils,
            "ensure_dir",
            return_value=None,
        ), mock.patch.object(
            docker_utils,
            "run_cmd_live",
            side_effect=fake_run_cmd_live,
        ):
            docker_utils.docker_tar_volume("demo-volume", Path("/app/data/backups/demo.tar.gz"))

        self.assertTrue(calls)
        self.assertEqual(calls[0][0:8], ["docker", "run", "--rm", "--entrypoint", "sh", "-v", "demo-volume:/data:ro", "-v"])
        self.assertIn("backend-helper:test", calls[0])

    def test_container_path_to_host_str_uses_mount_mapping(self):
        from backend.services.data_security.docker_utils import container_path_to_host_str

        mounts = [
            {"Destination": "/app/data", "Source": "/host/data"},
            {"Destination": "/app/uploads", "Source": "/host/uploads"},
        ]
        with mock.patch("backend.services.data_security.docker_utils._docker_self_mounts", return_value=mounts):
            self.assertEqual(
                container_path_to_host_str("/app/data/backups/migration_pack_x/volumes/a.tar.gz"),
                "/host/data/backups/migration_pack_x/volumes/a.tar.gz",
            )
            self.assertEqual(
                container_path_to_host_str("/app/data/auth.db"),
                "/host/data/auth.db",
            )
            self.assertEqual(
                container_path_to_host_str("/app/uploads/file.bin"),
                "/host/uploads/file.bin",
            )

    def test_container_path_to_host_str_rejects_managed_paths_without_mapping(self):
        from backend.services.data_security.docker_utils import container_path_to_host_str

        with mock.patch("backend.services.data_security.docker_utils._docker_self_mounts", return_value=[]), mock.patch(
            "backend.services.data_security.models._running_inside_container",
            return_value=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "container_mount_mapping_not_found:/app/data/auth.db"):
                container_path_to_host_str("/app/data/auth.db")

    def test_container_path_to_host_str_maps_managed_paths_on_host_runtime(self):
        from backend.services.data_security.docker_utils import container_path_to_host_str

        with mock.patch("backend.services.data_security.docker_utils._docker_self_mounts", return_value=[]), mock.patch(
            "backend.services.data_security.models._running_inside_container",
            return_value=False,
        ), mock.patch(
            "backend.services.data_security.models.managed_data_root",
            return_value=Path(r"D:\ProjectPackage\RagflowAuth\data"),
        ):
            mapped = container_path_to_host_str("/app/data/backups/migration_pack_x/volumes/a.tar.gz")

        self.assertEqual(mapped, r"D:\ProjectPackage\RagflowAuth\data\backups\migration_pack_x\volumes\a.tar.gz")

    def test_docker_save_images_uses_container_path_not_host_path(self):
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
