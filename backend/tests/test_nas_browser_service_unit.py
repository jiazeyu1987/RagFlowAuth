import unittest

from backend.services.nas_browser_service import NasBrowserService


class _FakeNasBrowserService(NasBrowserService):
    async def _import_single_file(self, *, source_path: str, target_filename: str, kb_ref: str, deps, ctx):
        return {
            "status": "skipped",
            "payload": {
                "path": source_path,
                "reason": "unsupported_extension",
                "detail": "unsupported extension: .exe",
            },
        }


class NasBrowserServiceUnitTests(unittest.TestCase):
    def test_collect_folder_files_sync_returns_structured_skipped_reason(self):
        service = NasBrowserService()
        service._get_smbclient = lambda: object()  # type: ignore[method-assign]
        service._register_session = lambda _client: None  # type: ignore[method-assign]
        service._walk_files_sync = lambda _client, _path: [  # type: ignore[method-assign]
            {"name": "a.pdf", "path": "folder/a.pdf"},
            {"name": "a.exe", "path": "folder/a.exe"},
        ]
        service._allowed_extensions = lambda _deps: {".pdf"}  # type: ignore[method-assign]

        supported, skipped = service._collect_folder_files_sync("folder", deps=object())

        self.assertEqual(len(supported), 1)
        self.assertEqual(supported[0]["path"], "folder/a.pdf")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["path"], "folder/a.exe")
        self.assertEqual(skipped[0]["reason"], "unsupported_extension")
        self.assertIn(".exe", skipped[0]["detail"])


class NasBrowserServiceAsyncUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_file_to_kb_returns_structured_skipped_payload(self):
        service = _FakeNasBrowserService()
        result = await service.import_file_to_kb(
            relative_path="folder/a.exe",
            kb_ref="kb1",
            deps=object(),
            ctx=object(),
        )

        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["skipped"][0]["path"], "folder/a.exe")
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_extension")


if __name__ == "__main__":
    unittest.main()
