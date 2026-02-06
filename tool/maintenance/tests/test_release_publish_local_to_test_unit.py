from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tool.maintenance.core.constants import TEST_SERVER_IP
from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir
from tool.maintenance.features import release_publish_local_to_test
from tool.maintenance.features.release_publish import ServerVersionInfo


class TestReleasePublishLocalToTestUnit(unittest.TestCase):
    def test_local_to_test_build_save_scp_and_recreate(self) -> None:
        tmp_root = make_temp_dir(prefix="ragflowauth_ut")

        calls: list[str] = []

        def fake_run_local(command: str, *, cwd=None, timeout_s: int = 3600):
            calls.append(command)
            if command.strip().startswith("ssh ") and "df -Pk" in command:
                # Filesystem 1024-blocks Used Available Capacity Mounted on
                return True, "/dev/vdb 102400 0 102400 0% /tmp"
            if command.strip().startswith("ssh ") and "echo OK" in command:
                return True, "OK"
            # Simulate docker save creating the tar file.
            if "docker save" in command and "-o" in command:
                # Extract quoted tar path (simple heuristic).
                marker = '-o "'
                if marker in command:
                    tar_path = command.split(marker, 1)[1].split('"', 1)[0]
                    Path(tar_path).write_bytes(b"tar")
            return True, "ok"

        before = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:old",
            frontend_image="ragflowauth-frontend:old",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )
        after = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:new",
            frontend_image="ragflowauth-frontend:new",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )

        with patch.object(release_publish_local_to_test, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish_local_to_test, "make_temp_dir", return_value=tmp_root
        ), patch.object(
            release_publish_local_to_test, "docker_load_tar_on_server", return_value=(True, "OK")
        ), patch.object(
            release_publish_local_to_test, "recreate_server_containers_from_inspect", return_value=(True, "OK")
        ) as mock_recreate, patch.object(
            release_publish_local_to_test, "preflight_check_ragflow_base_url", return_value=True
        ), patch.object(
            release_publish_local_to_test, "get_server_version_info", side_effect=[before, after]
        ):
            res = release_publish_local_to_test.publish_from_local_to_test(version="v123")
            self.assertTrue(res.ok, res.log)
            self.assertEqual(res.version_before, before)
            self.assertEqual(res.version_after, after)
        cleanup_dir(tmp_root)

        # Verify build commands use the unified tag
        self.assertTrue(any("docker build" in c and "ragflowauth-backend:v123" in c for c in calls), calls)
        self.assertTrue(any("docker build" in c and "ragflowauth-frontend:v123" in c for c in calls), calls)
        self.assertTrue(any("docker save" in c and "ragflowauth-backend:v123" in c and "ragflowauth-frontend:v123" in c for c in calls), calls)
        self.assertTrue(any(c.startswith("scp ") and f"root@{TEST_SERVER_IP}:" in c for c in calls), calls)

        mock_recreate.assert_called()

    def test_local_to_test_bootstrap_when_no_existing_containers(self) -> None:
        tmp_root = make_temp_dir(prefix="ragflowauth_ut")

        calls: list[str] = []

        def fake_run_local(command: str, *, cwd=None, timeout_s: int = 3600):
            calls.append(command)
            if command.strip().startswith("ssh ") and "df -Pk" in command:
                return True, "/dev/vdb 102400 0 102400 0% /tmp"
            if command.strip().startswith("ssh ") and "echo OK" in command:
                return True, "OK"
            # Simulate docker save creating the tar file.
            if "docker save" in command and "-o" in command:
                marker = '-o "'
                if marker in command:
                    tar_path = command.split(marker, 1)[1].split('"', 1)[0]
                    Path(tar_path).write_bytes(b"tar")
            return True, "ok"

        before = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:old",
            frontend_image="ragflowauth-frontend:old",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )
        after = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:new",
            frontend_image="ragflowauth-frontend:new",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )

        with patch.object(release_publish_local_to_test, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish_local_to_test, "make_temp_dir", return_value=tmp_root
        ), patch.object(
            release_publish_local_to_test, "docker_load_tar_on_server", return_value=(True, "OK")
        ), patch.object(
            release_publish_local_to_test,
            "recreate_server_containers_from_inspect",
            return_value=(False, "containers not found (ragflowauth-backend/frontend)"),
        ) as mock_recreate, patch.object(
            release_publish_local_to_test, "bootstrap_server_containers", return_value=(True, "OK")
        ), patch.object(
            release_publish_local_to_test, "preflight_check_ragflow_base_url", return_value=True
        ) as mock_bootstrap, patch.object(
            release_publish_local_to_test, "get_server_version_info", side_effect=[before, after]
        ):
            res = release_publish_local_to_test.publish_from_local_to_test(version="v123")
            self.assertTrue(res.ok, res.log)
        cleanup_dir(tmp_root)

        mock_recreate.assert_called()
        mock_bootstrap.assert_called()

    def test_ui_log_callback_receives_progress_lines(self) -> None:
        tmp_root = make_temp_dir(prefix="ragflowauth_ut")

        def fake_run_local(command: str, *, cwd=None, timeout_s: int = 3600):
            # Simulate docker save creating the tar file.
            if command.strip().startswith("ssh ") and "df -Pk" in command:
                return True, "/dev/vdb 102400 0 102400 0% /tmp"
            if command.strip().startswith("ssh ") and "echo OK" in command:
                return True, "OK"
            if "docker save" in command and "-o" in command:
                marker = '-o "'
                if marker in command:
                    tar_path = command.split(marker, 1)[1].split('"', 1)[0]
                    Path(tar_path).write_bytes(b"tar")
            return True, "ok"

        before = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:old",
            frontend_image="ragflowauth-frontend:old",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )
        after = ServerVersionInfo(
            server_ip=TEST_SERVER_IP,
            backend_image="ragflowauth-backend:new",
            frontend_image="ragflowauth-frontend:new",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )

        ui_lines: list[str] = []

        with patch.object(release_publish_local_to_test, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish_local_to_test, "make_temp_dir", return_value=tmp_root
        ), patch.object(
            release_publish_local_to_test, "docker_load_tar_on_server", return_value=(True, "OK")
        ), patch.object(
            release_publish_local_to_test, "recreate_server_containers_from_inspect", return_value=(True, "OK")
        ), patch.object(
            release_publish_local_to_test, "preflight_check_ragflow_base_url", return_value=True
        ), patch.object(
            release_publish_local_to_test, "get_server_version_info", side_effect=[before, after]
        ):
            res = release_publish_local_to_test.publish_from_local_to_test(version="v123", ui_log=ui_lines.append)
            self.assertTrue(res.ok, res.log)

        self.assertTrue(any("LOCAL -> TEST" in ln for ln in ui_lines), ui_lines[:5])
        cleanup_dir(tmp_root)
