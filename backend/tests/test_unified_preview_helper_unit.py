import unittest
from unittest.mock import patch

from backend.services.unified_preview import build_preview_payload


class TestUnifiedPreviewHelperUnit(unittest.TestCase):
    def test_text_utf8(self):
        p = build_preview_payload("hi".encode("utf-8"), "a.txt", doc_id="d1")
        self.assertEqual(p["type"], "text")
        self.assertEqual(p["filename"], "a.txt")
        self.assertEqual(p["content"], "hi")

    def test_pdf_base64(self):
        p = build_preview_payload(b"%PDF-1.4", "a.pdf", doc_id="d1")
        self.assertEqual(p["type"], "pdf")
        self.assertEqual(p["filename"], "a.pdf")
        self.assertTrue(isinstance(p.get("content"), str))
        self.assertGreater(len(p["content"]), 0)

    def test_image_base64(self):
        p = build_preview_payload(b"xxxx", "a.png", doc_id="d1")
        self.assertEqual(p["type"], "image")
        self.assertEqual(p["image_type"], "png")
        self.assertTrue(isinstance(p.get("content"), str))

    def test_docx_fallback_when_soffice_missing(self):
        with patch("backend.services.office_to_html.convert_office_bytes_to_html_bytes", side_effect=RuntimeError("soffice not found")):
            with patch(
                "backend.services.docx_to_html_fallback.convert_docx_bytes_to_html_bytes_fallback",
                return_value=b"<html>ok</html>",
            ):
                p = build_preview_payload(b"not-a-real-docx", "a.docx", doc_id="d1")
        self.assertEqual(p["type"], "html")
        self.assertTrue(p["filename"].endswith(".html"))
        self.assertTrue(isinstance(p.get("content"), str))

