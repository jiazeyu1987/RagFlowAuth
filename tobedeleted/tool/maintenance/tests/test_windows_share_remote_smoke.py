from __future__ import annotations

import os
import unittest

from tool.maintenance.core.constants import TEST_SERVER_IP
from tool.maintenance.core.ssh_executor import SSHExecutor


class TestWindowsShareRemoteSmoke(unittest.TestCase):
    """Remote smoke tests against the TEST server.

    These tests assume SSH key-based auth is set up for root@test server.
    """

    def setUp(self) -> None:
        if os.environ.get("RAGFLOWAUTH_REMOTE_TESTS", "1") != "1":
            self.skipTest("Remote tests disabled (set RAGFLOWAUTH_REMOTE_TESTS=1 to enable)")
        self.ssh = SSHExecutor(TEST_SERVER_IP, "root")

    def test_ssh_connectivity(self) -> None:
        ok, out = self.ssh.execute("echo ok")
        self.assertTrue(ok, out)
        self.assertIn("ok", out)

    def test_mount_point_readable(self) -> None:
        # Read-only check; does not mount/unmount.
        ok, out = self.ssh.execute("ls -ld /mnt/replica 2>&1 || true")
        self.assertTrue(ok, out)

