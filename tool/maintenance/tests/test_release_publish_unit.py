from __future__ import annotations

import unittest
from unittest.mock import patch

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.features import release_publish


class TestReleasePublishUnit(unittest.TestCase):
    def test_scp_uses_streaming_remote_to_remote(self) -> None:
        calls: list[list[str]] = []

        def fake_run_local(argv: list[str], *, timeout_s: int = 3600):
            calls.append(argv)
            return True, "ok"

        # Make ssh calls succeed without touching real servers.
        with patch.object(release_publish, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish, "_ssh_cmd", return_value=(True, "OK")
        ), patch.object(release_publish, "_docker_inspect", return_value={"HostConfig": {"NetworkMode": "ragflowauth-network"}}), patch.object(
            release_publish, "_build_recreate_from_inspect", return_value="echo docker-run"
        ), patch.object(release_publish, "_ensure_network", return_value=(True, "")), patch.object(
            release_publish, "_wait_prod_ready", return_value=(True, "OK")
        ), patch.object(
            release_publish, "preflight_check_ragflow_base_url", return_value=True
        ), patch.object(
            release_publish, "get_server_version_info"
        ) as mock_ver:
            mock_ver.side_effect = [
                release_publish.ServerVersionInfo(
                    server_ip=PROD_SERVER_IP,
                    backend_image="ragflowauth-backend:prev",
                    frontend_image="ragflowauth-frontend:prev",
                    compose_path="/opt/ragflowauth/docker-compose.yml",
                    env_path="/opt/ragflowauth/.env",
                    compose_sha256="x",
                    env_sha256="y",
                ),
                release_publish.ServerVersionInfo(
                    server_ip=TEST_SERVER_IP,
                    backend_image="ragflowauth-backend:testtag",
                    frontend_image="ragflowauth-frontend:testtag",
                    compose_path="/opt/ragflowauth/docker-compose.yml",
                    env_path="/opt/ragflowauth/.env",
                    compose_sha256="a",
                    env_sha256="b",
                ),
                release_publish.ServerVersionInfo(
                    server_ip=PROD_SERVER_IP,
                    backend_image="ragflowauth-backend:testtag",
                    frontend_image="ragflowauth-frontend:testtag",
                    compose_path="/opt/ragflowauth/docker-compose.yml",
                    env_path="/opt/ragflowauth/.env",
                    compose_sha256="a",
                    env_sha256="b",
                ),
            ]

            res = release_publish.publish_from_test_to_prod(version="v1")
            self.assertTrue(res.ok, res.log)

        self.assertTrue(calls, "expected scp calls")
        # First call: tar transfer should use scp -3 and fixed ips.
        self.assertEqual(calls[0][0:2], ["scp", "-3"])
        self.assertIn(f"{DEFAULT_SERVER_USER}@{TEST_SERVER_IP}:", calls[0][-2])
        self.assertIn(f"{DEFAULT_SERVER_USER}@{PROD_SERVER_IP}:", calls[0][-1])

    def test_run_mode_when_no_compose(self) -> None:
        calls: list[list[str]] = []

        def fake_run_local(argv: list[str], *, timeout_s: int = 3600):
            calls.append(argv)
            return True, "ok"

        # Simulate: compose missing on TEST; should still transfer tar, but must NOT attempt scp compose/env.
        with patch.object(release_publish, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish, "_ssh_cmd", return_value=(True, "OK")
        ), patch.object(
            release_publish, "_docker_inspect", return_value={"HostConfig": {"NetworkMode": "ragflowauth-network"}}  # minimal
        ), patch.object(
            release_publish, "_build_recreate_from_inspect", return_value="echo docker-run"
        ), patch.object(
            release_publish, "_ensure_network", return_value=(True, "")
        ), patch.object(
            release_publish, "_wait_prod_ready", return_value=(True, "OK")
        ), patch.object(
            release_publish, "preflight_check_ragflow_base_url", return_value=True
        ), patch.object(
            release_publish, "get_server_version_info"
        ) as mock_ver:
            mock_ver.side_effect = [
                release_publish.ServerVersionInfo(
                    server_ip=PROD_SERVER_IP,
                    backend_image="ragflowauth-backend:prev",
                    frontend_image="ragflowauth-frontend:prev",
                    compose_path="",
                    env_path="",
                    compose_sha256="",
                    env_sha256="",
                ),
                release_publish.ServerVersionInfo(
                    server_ip=TEST_SERVER_IP,
                    backend_image="ragflowauth-backend:testtag",
                    frontend_image="ragflowauth-frontend:testtag",
                    compose_path="",
                    env_path="",
                    compose_sha256="",
                    env_sha256="",
                ),
                release_publish.ServerVersionInfo(
                    server_ip=PROD_SERVER_IP,
                    backend_image="ragflowauth-backend:testtag",
                    frontend_image="ragflowauth-frontend:testtag",
                    compose_path="",
                    env_path="",
                    compose_sha256="",
                    env_sha256="",
                ),
            ]

            res = release_publish.publish_from_test_to_prod(version="v2")
            self.assertTrue(res.ok, res.log)

        # Only tar transfer via scp -3 should happen (single scp call).
        scp_calls = [c for c in calls if c and c[0] == "scp"]
        self.assertEqual(len(scp_calls), 1, scp_calls)
        self.assertEqual(scp_calls[0][0:2], ["scp", "-3"])

    def test_preflight_blocks_publish(self) -> None:
        with patch.object(release_publish, "preflight_check_ragflow_base_url", return_value=False), patch.object(
            release_publish, "get_server_version_info"
        ) as mock_ver:
            mock_ver.side_effect = [
                release_publish.ServerVersionInfo(
                    server_ip=PROD_SERVER_IP,
                    backend_image="ragflowauth-backend:prev",
                    frontend_image="ragflowauth-frontend:prev",
                    compose_path="",
                    env_path="",
                    compose_sha256="",
                    env_sha256="",
                ),
                release_publish.ServerVersionInfo(
                    server_ip=TEST_SERVER_IP,
                    backend_image="ragflowauth-backend:testtag",
                    frontend_image="ragflowauth-frontend:testtag",
                    compose_path="",
                    env_path="",
                    compose_sha256="",
                    env_sha256="",
                ),
            ]
            res = release_publish.publish_from_test_to_prod(version="v3")
            self.assertFalse(res.ok)
            self.assertIn("Preflight check failed", res.log)
