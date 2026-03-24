import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.database.schema import ensure_schema
from backend.services.package_drawing.manager import (
    PackageDrawingImportError,
    PackageDrawingManager,
    _RowImage,
)
from backend.services.package_drawing.store import PackageDrawingStore


class _UploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class TestPackageDrawingManagerUnit(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._db_path = str(Path(self._tmp.name) / "auth.db")
        ensure_schema(self._db_path)
        self.store = PackageDrawingStore(db_path=self._db_path)
        deps = SimpleNamespace(package_drawing_store=self.store)
        self.manager = PackageDrawingManager(deps)
        self._old_image_root = self.manager._image_root
        self.manager._image_root = Path(self._tmp.name) / "images"
        self.manager._image_root.mkdir(parents=True, exist_ok=True)

    async def asyncTearDown(self):
        self.manager._image_root = self._old_image_root
        self._tmp.cleanup()

    async def test_import_xlsx_supports_upsert_and_partial_errors(self):
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "S1"
        ws.append(["型号", "条形码", "产品参数A", "产品参数B", "示意图"])
        ws.append(["M-001", "BC-OLD", "参数值A-旧", "参数值B-旧", "https://example.com/old.png"])
        ws.append(["M-001", "BC-NEW", "参数值A-新", "参数值B-新", "https://example.com/new.png"])
        ws.append(["", "BC-X", "缺少型号", "", ""])

        buf = io.BytesIO()
        wb.save(buf)
        upload = _UploadFile(filename="sample.xlsx", content=buf.getvalue())

        result = await self.manager.import_from_upload(upload)
        self.assertEqual(result["rows_scanned"], 3)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["success"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual((result["errors"] or [])[0]["reason"], "missing_model")

        payload = self.manager.query_by_model("M-001")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["barcode"], "BC-NEW")
        self.assertEqual(payload["parameters"]["产品参数A"], "参数值A-新")
        self.assertEqual(payload["parameters"]["产品参数B"], "参数值B-新")
        self.assertEqual(len(payload["images"]), 1)
        self.assertEqual(payload["images"][0]["url"], "https://example.com/new.png")

    async def test_import_embedded_image_can_be_queried(self):
        self.manager._parse_workbook = lambda _content: {
            "records": {
                "M-EMB": {
                    "sheet": "SHEET1",
                    "row": 2,
                    "barcode": "BC-EMB",
                    "parameters": {"规格": "A1"},
                    "images": [
                        _RowImage(
                            source_type="embedded",
                            image_url="",
                            rel_path="",
                            mime_type="image/png",
                            filename="demo.png",
                            content=b"\x89PNG\r\n\x1a\n",
                        )
                    ],
                }
            },
            "errors": [],
            "rows_scanned": 1,
        }

        upload = _UploadFile(filename="embedded.xlsx", content=b"mock")
        result = await self.manager.import_from_upload(upload)
        self.assertEqual(result["success"], 1)

        payload = self.manager.query_by_model("M-EMB")
        self.assertIsNotNone(payload)
        self.assertEqual(len(payload["images"]), 1)
        self.assertTrue(str(payload["images"][0]["data_url"]).startswith("data:image/png;base64,"))

        record = self.store.get_record("M-EMB")
        self.assertIsNotNone(record)
        image_id = record.images[0].image_id
        image_payload = self.manager.get_image_binary(image_id)
        self.assertIsNotNone(image_payload)
        content, filename, mime_type = image_payload
        self.assertEqual(content, b"\x89PNG\r\n\x1a\n")
        self.assertEqual(filename, "demo.png")
        self.assertEqual(mime_type, "image/png")

    async def test_import_rejects_non_xlsx(self):
        upload = _UploadFile(filename="bad.xls", content=b"abc")
        with self.assertRaises(PackageDrawingImportError) as cm:
            await self.manager.import_from_upload(upload)
        self.assertEqual(cm.exception.code, "only_xlsx_supported")


if __name__ == "__main__":
    unittest.main()
