import tempfile
import unittest
from pathlib import Path


class TestReleaseHistoryUnit(unittest.TestCase):
    def test_missing_file_returns_helpful_message(self) -> None:
        from tool.maintenance.features.release_history import load_release_history

        view = load_release_history(path="this/path/does/not/exist.md", tail_lines=50)
        self.assertFalse(view.ok)
        self.assertIn("文件不存在", view.text)

    def test_tail_lines_returns_last_lines(self) -> None:
        from tool.maintenance.features.release_history import load_release_history

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "release_history.md"
            p.write_text("\n".join([f"line{i}" for i in range(10)]) + "\n", encoding="utf-8")

            view = load_release_history(path=str(p), tail_lines=3)
            self.assertTrue(view.ok)
            self.assertIn("显示最后 3 行", view.text)
            self.assertIn("line7", view.text)
            self.assertIn("line8", view.text)
            self.assertIn("line9", view.text)
            self.assertNotIn("line0", view.text)

