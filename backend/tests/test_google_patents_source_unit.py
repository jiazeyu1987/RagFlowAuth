import unittest

from backend.services.patent_download.sources.base import PatentSourceError
from backend.services.patent_download.sources.google_patents import GooglePatentsSource


class TestGooglePatentsSourceUnit(unittest.TestCase):
    def test_extract_candidates_raises_on_unexpected_payload(self):
        source = GooglePatentsSource()

        with self.assertRaises(PatentSourceError) as cm:
            source._extract_candidates_from_payload({"foo": "bar"}, limit=10)

        self.assertIn("google_query_unexpected_payload", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
