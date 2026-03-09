import unittest


class TestDownloadCommonExportsUnit(unittest.TestCase):
    def test_lazy_exports_are_available(self):
        from backend.services import download_common

        self.assertTrue(hasattr(download_common, "BaseDownloadManager"))
        self.assertTrue(hasattr(download_common, "BaseDownloadStore"))
        self.assertEqual(download_common.BaseDownloadManager.__name__, "BaseDownloadManager")
        self.assertEqual(download_common.BaseDownloadStore.__name__, "BaseDownloadStore")


if __name__ == "__main__":
    unittest.main()
