import unittest
from pathlib import Path

from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir


class TestReleaseHistoryUnit(unittest.TestCase):
    def test_missing_file_returns_helpful_message(self) -> None:
        from tool.maintenance.features.release_history import load_release_history

        view = load_release_history(path="this/path/does/not/exist.md", tail_lines=50)
        self.assertFalse(view.ok)
        self.assertIn("exist.md", view.text)

    def test_tail_lines_returns_last_lines(self) -> None:
        from tool.maintenance.features.release_history import load_release_history

        td = make_temp_dir(prefix="ragflowauth_release_history")
        try:
            p = Path(td) / "release_history.md"
            p.write_text("\n".join([f"line{i}" for i in range(10)]) + "\n", encoding="utf-8")

            view = load_release_history(path=str(p), tail_lines=3)
            self.assertTrue(view.ok)
            self.assertIn("line7", view.text)
            self.assertIn("line8", view.text)
            self.assertIn("line9", view.text)
            self.assertNotIn("line0", view.text)
        finally:
            cleanup_dir(td)
