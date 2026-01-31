from __future__ import annotations

import unittest

from tool.maintenance.core.constants import TEST_SERVER_IP


class TestTargets(unittest.TestCase):
    def test_test_server_ip_is_fixed(self) -> None:
        self.assertEqual(TEST_SERVER_IP, "172.30.30.58")

