from __future__ import annotations

import os
import unittest

from tool.maintenance.core.constants import TEST_SERVER_IP
from tool.maintenance.core.ssh_executor import SSHExecutor


class TestRemoteDockerSmoke(unittest.TestCase):
    def setUp(self) -> None:
        if os.environ.get("RAGFLOWAUTH_REMOTE_TESTS", "1") != "1":
            self.skipTest("Remote tests disabled (set RAGFLOWAUTH_REMOTE_TESTS=1 to enable)")
        self.ssh = SSHExecutor(TEST_SERVER_IP, "root")

    def test_docker_available(self) -> None:
        ok, out = self.ssh.execute("docker --version 2>&1")
        self.assertTrue(ok, out)

