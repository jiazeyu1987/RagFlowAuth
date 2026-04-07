from __future__ import annotations

import unittest

from tool.maintenance.core.constants import (
    MOUNT_POINT,
    SCRIPTS_DIR,
)


class TestWindowsShareScripts(unittest.TestCase):
    def test_mount_script_contains_invariants(self) -> None:
        script = (SCRIPTS_DIR / "mount-windows-share.ps1").read_text(encoding="utf-8", errors="replace")
        self.assertIn(MOUNT_POINT, script)
        self.assertIn("RagflowAuth", script)
        # The script is parameterized for WindowsHost/ShareName; fixed values live in tool.py.
        self.assertIn("$WindowsHost", script)
        self.assertIn("$ShareName", script)
        self.assertIn("mount -t cifs", script)

    def test_unmount_script_contains_invariants(self) -> None:
        script = (SCRIPTS_DIR / "unmount-windows-share.ps1").read_text(encoding="utf-8", errors="replace")
        self.assertIn(MOUNT_POINT, script)

    def test_check_script_contains_invariants(self) -> None:
        script = (SCRIPTS_DIR / "check-mount-status.ps1").read_text(encoding="utf-8", errors="replace")
        self.assertIn(MOUNT_POINT, script)
