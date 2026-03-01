import unittest

from backend.services.paper_download.sources import PaperSourceFactory
from backend.services.patent_download.sources import PatentSourceFactory


class TestDownloadSourceFactoryUnit(unittest.TestCase):
    def test_patent_source_factory_builds_expected_registry(self):
        factory = PatentSourceFactory()

        registry = factory.create_registry()
        mapping = registry.build_mapping()

        self.assertEqual(set(mapping.keys()), {"google_patents", "uspto"})
        self.assertEqual(mapping["google_patents"].SOURCE_LABEL, "Google Patents")
        self.assertTrue(hasattr(mapping["uspto"], "_google_source"))
        self.assertIs(mapping["uspto"]._google_source, mapping["google_patents"])

    def test_paper_source_factory_builds_expected_registry(self):
        factory = PaperSourceFactory()

        registry = factory.create_registry()
        mapping = registry.build_mapping()

        self.assertEqual(set(mapping.keys()), {"arxiv", "pubmed", "europe_pmc", "openalex"})
        self.assertEqual(mapping["arxiv"].SOURCE_LABEL, "arXiv")
        self.assertEqual(mapping["openalex"].SOURCE_LABEL, "OpenAlex")


if __name__ == "__main__":
    unittest.main()
