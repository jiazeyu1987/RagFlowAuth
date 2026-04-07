from __future__ import annotations

import unittest

from tool.maintenance.core.remote_staging import RemoteStagingManager


class TestRemoteStagingUnit(unittest.TestCase):
    def test_cleanup_legacy_tmp_release_files_is_best_effort(self) -> None:
        log_lines: list[str] = []

        def raising_exec(_: str):
            raise TimeoutError("Command timed out after 60 seconds")

        mgr = RemoteStagingManager(exec_fn=raising_exec, log=log_lines.append)
        mgr.cleanup_legacy_tmp_release_files()

        self.assertTrue(any("cleanup legacy /tmp release artifacts failed" in line for line in log_lines), log_lines)


if __name__ == "__main__":
    unittest.main()
