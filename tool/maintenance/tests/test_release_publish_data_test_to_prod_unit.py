from __future__ import annotations

import unittest
from unittest.mock import patch

from tool.maintenance.core.constants import PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.features import release_publish_data_test_to_prod
from tool.maintenance.features.release_publish import ServerVersionInfo


class TestReleasePublishDataTestToProdUnit(unittest.TestCase):
    def test_uses_scp_3_and_fixes_prod_base_url(self) -> None:
        calls_local: list[list[str]] = []
        calls_ssh: list[tuple[str, str]] = []

        def fake_run_local(argv: list[str], *, timeout_s: int = 7200):
            calls_local.append(argv)
            return True, "ok"

        def fake_ssh(ip: str, cmd: str):
            calls_ssh.append((ip, cmd))
            # base_url reads
            if "sed -n" in cmd and "ragflow_config.json" in cmd:
                if ip == TEST_SERVER_IP:
                    return True, f"http://{TEST_SERVER_IP}:9380"
                if ip == PROD_SERVER_IP:
                    return True, f"http://{PROD_SERVER_IP}:9380"
            # stop verification checks
            if "RAGFLOWAUTH_STOP_CHECK" in cmd:
                return True, "STOPPED"
            if "infiniflow/ragflow" in cmd and "docker ps" in cmd:
                return True, "OK"
            return True, "OK"

        before = ServerVersionInfo(
            server_ip=PROD_SERVER_IP,
            backend_image="ragflowauth-backend:prev",
            frontend_image="ragflowauth-frontend:prev",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )
        after = ServerVersionInfo(
            server_ip=PROD_SERVER_IP,
            backend_image="ragflowauth-backend:prev",
            frontend_image="ragflowauth-frontend:prev",
            compose_path="",
            env_path="",
            compose_sha256="",
            env_sha256="",
        )

        with patch.object(release_publish_data_test_to_prod, "_run_local", side_effect=fake_run_local), patch.object(
            release_publish_data_test_to_prod, "_ssh", side_effect=fake_ssh
        ), patch.object(
            release_publish_data_test_to_prod, "_wait_for_container_running", return_value=True
        ), patch.object(
            release_publish_data_test_to_prod, "_docker_container_status_and_ip", return_value=(True, "running", "172.18.0.6")
        ), patch.object(release_publish_data_test_to_prod, "get_server_version_info", side_effect=[before, after]):
            res = release_publish_data_test_to_prod.publish_data_from_test_to_prod(version="v1")
            self.assertTrue(res.ok, res.log)

        scp_calls = [c for c in calls_local if c and c[0] == "scp"]
        self.assertTrue(scp_calls, "expected scp calls")
        self.assertEqual(scp_calls[0][0:2], ["scp", "-3"])
        self.assertTrue(any(f"root@{TEST_SERVER_IP}:" in a for a in scp_calls[0]), "missing TEST scp source")
        self.assertTrue(any(f"root@{PROD_SERVER_IP}:" in a for a in scp_calls[0]), "missing PROD scp dest")

        # base_url should be read on both servers
        read_test = any(ip == TEST_SERVER_IP and "ragflow_config.json" in cmd and "sed -n" in cmd for ip, cmd in calls_ssh)
        read_prod = any(ip == PROD_SERVER_IP and "ragflow_config.json" in cmd and "sed -n" in cmd for ip, cmd in calls_ssh)
        self.assertTrue(read_test)
        self.assertTrue(read_prod)

        # Stop/verify should include the "stop ragflow stack by image" fallback (not name-prefix only).
        has_stop_by_image = any(
            "docker ps -q" in cmd and "ancestor=infiniflow/ragflow" in cmd and "sort -u" in cmd for _, cmd in calls_ssh
        )
        self.assertTrue(has_stop_by_image, "expected stop-by-image fallback in ssh commands")
