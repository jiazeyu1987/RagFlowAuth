import base64
import io
import unittest
import zipfile

from backend.services.docx_to_html_fallback import convert_docx_bytes_to_html_bytes_fallback


def _make_minimal_docx_bytes(text: str) -> bytes:
    """
    Create a minimal DOCX-like zip that contains word/document.xml.
    This is sufficient for our fallback preview extractor.
    """

    doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
""".encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


class TestDocxPreviewFallbackUnit(unittest.TestCase):
    def test_fallback_extracts_text_to_html(self):
        docx_bytes = _make_minimal_docx_bytes("Hello DOCX")
        html_bytes = convert_docx_bytes_to_html_bytes_fallback(docx_bytes)
        html = html_bytes.decode("utf-8", errors="ignore")
        self.assertIn("Hello DOCX", html)

    def test_fallback_is_html_bytes(self):
        docx_bytes = _make_minimal_docx_bytes("X")
        html_bytes = convert_docx_bytes_to_html_bytes_fallback(docx_bytes)
        # Ensure it can be safely base64 encoded for /preview JSON response.
        base64.b64encode(html_bytes).decode("ascii")
