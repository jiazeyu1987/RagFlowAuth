from __future__ import annotations

import os
import unittest

from tool.maintenance.core.constants import TEST_SERVER_IP
from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.features.docker_containers_with_mounts import show_containers_with_mounts
from tool.maintenance.features.windows_share_status import check_mount_status


class TestIntegrationAllFeatures(unittest.TestCase):
    """Integration test that exercises the core maintenance flows against the test server."""

    def setUp(self) -> None:
        if os.environ.get("RAGFLOWAUTH_REMOTE_TESTS", "1") != "1":
            self.skipTest("Remote tests disabled (set RAGFLOWAUTH_REMOTE_TESTS=1 to enable)")
        self.server_host = TEST_SERVER_IP
        self.server_user = "root"
        self.ssh = SSHExecutor(self.server_host, self.server_user)

    def test_all_features_smoke(self) -> None:
        ok, out = self.ssh.execute("echo tool-smoke")
        self.assertTrue(ok, out)

        # Feature 1: Check mount status (runs PowerShell locally and checks server via SSH).
        status = check_mount_status(server_host=self.server_host, server_user=self.server_user)
        self.assertEqual(status.returncode, 0, status.log_content or status.stderr)

        # Feature 2: Container + mount report (read-only).
        report = show_containers_with_mounts(ssh=self.ssh, log=lambda *_: None)
        self.assertIn("运行中的容器", report.text)
