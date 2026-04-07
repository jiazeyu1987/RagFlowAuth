from __future__ import annotations

import unittest
from pathlib import Path


class TestReleaseDockerignoreUnit(unittest.TestCase):
    def test_release_build_context_excludes_backend_test_temp_dirs(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        dockerignore = (repo_root / ".dockerignore").read_text(encoding="utf-8")

        self.assertIn("backend/tests/_tmp/", dockerignore)
        self.assertIn("backend/tests/_tmp/**", dockerignore)
        self.assertIn("backend/tests/_tmp_local/", dockerignore)
        self.assertIn("backend/tests/_tmp_local/**", dockerignore)


if __name__ == "__main__":
    unittest.main()
