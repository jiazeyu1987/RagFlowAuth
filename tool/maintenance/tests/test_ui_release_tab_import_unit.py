import unittest


class TestUIReleaseTabImportUnit(unittest.TestCase):
    def test_imports(self):
        from tool.maintenance.ui.release_tab import build_release_tab

        self.assertTrue(callable(build_release_tab))

