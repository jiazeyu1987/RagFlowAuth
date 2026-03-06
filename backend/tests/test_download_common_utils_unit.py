import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.services.download_common import utils


class TestDownloadCommonUtilsUnit(unittest.TestCase):
    def test_parse_keywords_and_build_query(self):
        keywords = utils.parse_keywords("AI, \u533b\u7597;ai\n \u533b\u7597\u5668\u68b0 \r;")
        self.assertEqual(keywords, ["AI", "\u533b\u7597", "\u533b\u7597\u5668\u68b0"])

        self.assertEqual(utils.build_query([], use_and=True), "")
        self.assertEqual(utils.build_query(["AI"], use_and=True), "AI")
        self.assertEqual(utils.build_query(["AI", "\u533b\u7597"], use_and=True), "AI \u533b\u7597")
        self.assertEqual(utils.build_query(["AI", "\u533b\u7597"], use_and=False), "AI OR \u533b\u7597")

    def test_flags_and_text_helpers(self):
        self.assertTrue(utils.is_downloaded_status("downloaded"))
        self.assertTrue(utils.is_downloaded_status("downloaded_cached"))
        self.assertFalse(utils.is_downloaded_status("failed"))

        self.assertTrue(utils.is_truthy_flag("true"))
        self.assertTrue(utils.is_truthy_flag("1"))
        self.assertFalse(utils.is_truthy_flag("0"))

        self.assertTrue(utils.contains_chinese("abc\u4e2d\u6587"))
        self.assertFalse(utils.contains_chinese("abc123"))

        self.assertEqual(utils.strip_html_text("<div>A&nbsp;B</div>"), "A B")
        self.assertEqual(utils.normalize_match_text(" A  B\tC "), "abc")

    def test_filename_and_content_disposition(self):
        self.assertEqual(utils.safe_pdf_filename("a:b", "", default_base="paper"), "a_b.pdf")
        self.assertEqual(utils.safe_pdf_filename("", "", default_base="paper"), "paper.pdf")
        self.assertEqual(utils.safe_pdf_filename("already.pdf", "", default_base="paper"), "already.pdf")

        ascii_cd = utils.build_content_disposition("report.pdf")
        self.assertIn('filename="report.pdf"', ascii_cd)

        utf8_cd = utils.build_content_disposition("\u62a5\u544a.pdf")
        self.assertIn("filename*=", utf8_cd)
        self.assertIn("UTF-8", utf8_cd)

    def test_translator_helpers(self):
        stdout = "ZH: \u4e2d\u6587\nEN: medical device\n"
        self.assertEqual(utils.parse_translator_output(stdout), "medical device")

        missing = Path("D:/__definitely_missing_translate_script__.py")
        with self.assertRaises(RuntimeError):
            utils.translate_query_for_uspto("\u533b\u7597", script_path=missing, timeout=1)

    @patch("backend.services.download_common.utils.urllib.request.urlopen")
    def test_download_pdf_bytes(self, mock_urlopen):
        fake_response = MagicMock()
        fake_response.read.return_value = b"PDF-BYTES"
        fake_context = MagicMock()
        fake_context.__enter__.return_value = fake_response
        fake_context.__exit__.return_value = None
        mock_urlopen.return_value = fake_context

        data = utils.download_pdf_bytes("https://example.com/file.pdf", user_agent="UnitTest-UA", timeout=5)
        self.assertEqual(data, b"PDF-BYTES")
        self.assertEqual(mock_urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
