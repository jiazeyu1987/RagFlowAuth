import unittest

from backend.services.download_connectors import (
    DownloadCandidate,
    DownloadSourceDescriptor,
    DownloadSourceRegistryManager,
)


class _FakeSource:
    SOURCE_KEY = "fake_source"
    SOURCE_LABEL = "Fake Source"

    def search(self, *, query: str, limit: int) -> list[DownloadCandidate]:  # noqa: ARG002
        return [
            DownloadCandidate(
                source=self.SOURCE_KEY,
                source_label=self.SOURCE_LABEL,
                patent_id="id-1",
                title="title",
                abstract_text="abstract",
                publication_number="pub-1",
                publication_date="2026-01-01",
                inventor="inventor",
                assignee="assignee",
                detail_url="https://example.com/detail",
                pdf_url="https://example.com/file.pdf",
            )
        ]


class TestDownloadSourceRegistryManagerUnit(unittest.TestCase):
    def test_register_get_and_build_mapping(self):
        registry = DownloadSourceRegistryManager()
        source = _FakeSource()

        registry.register(source)

        mapping = registry.build_mapping()
        self.assertIn("fake_source", mapping)
        self.assertIs(mapping["fake_source"], source)
        self.assertIs(registry.get("fake_source"), source)

    def test_list_descriptors_and_replace_same_key(self):
        registry = DownloadSourceRegistryManager()

        first = _FakeSource()
        second = _FakeSource()
        second.SOURCE_LABEL = "Fake Source 2"
        registry.register(first)
        registry.register(second)

        descriptors = registry.list_descriptors()
        self.assertEqual(descriptors, [DownloadSourceDescriptor(key="fake_source", label="Fake Source 2")])


if __name__ == "__main__":
    unittest.main()
