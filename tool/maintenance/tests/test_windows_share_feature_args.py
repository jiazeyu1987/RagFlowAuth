from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tool.maintenance.core.constants import (
    DEFAULT_WINDOWS_SHARE_HOST,
    DEFAULT_WINDOWS_SHARE_NAME,
    DEFAULT_WINDOWS_SHARE_PASSWORD,
    DEFAULT_WINDOWS_SHARE_USERNAME,
)
from tool.maintenance.features.windows_share_mount import mount_windows_share


class TestWindowsShareFeatureArgs(unittest.TestCase):
    @patch("tool.maintenance.features.windows_share_mount.subprocess.run")
    def test_mount_calls_powershell_with_fixed_share(self, run_mock: MagicMock) -> None:
        run_mock.return_value = type("R", (), {"returncode": 0, "stderr": ""})()
        res = mount_windows_share(server_host="172.30.30.58", server_user="root")
        self.assertTrue(res.ok)
        args = run_mock.call_args[0][0]
        self.assertIn("-WindowsHost", args)
        self.assertIn(DEFAULT_WINDOWS_SHARE_HOST, args)
        self.assertIn(DEFAULT_WINDOWS_SHARE_NAME, args)
        self.assertIn(DEFAULT_WINDOWS_SHARE_USERNAME, args)
        self.assertIn(DEFAULT_WINDOWS_SHARE_PASSWORD, args)

