import unittest
from types import SimpleNamespace

from backend.services.ragflow_service import RagflowService


class _DatasetObj:
    def __init__(self, dataset_id: str, name: str):
        self.id = dataset_id
        self.name = name


class _ClientWithGetDataset:
    def __init__(self, dataset):
        self.dataset = dataset
        self.calls: list[str] = []

    def get_dataset(self, name: str):
        self.calls.append(name)
        if getattr(self.dataset, "name", None) == name:
            return self.dataset
        return None


class _ClientWithPagedList:
    def __init__(self, pages: dict[int, list[object]]):
        self.pages = pages
        self.calls: list[dict[str, object]] = []

    def list_datasets(self, page: int = 1, page_size: int = 30, name: str | None = None, **kwargs):  # noqa: ARG002
        self.calls.append({"page": page, "page_size": page_size, "name": name})
        return list(self.pages.get(page, []))


class TestRagflowServiceDatasetLookupUnit(unittest.TestCase):
    def _build_service(self, client):
        svc = RagflowService.__new__(RagflowService)
        svc.client = client
        svc.logger = SimpleNamespace(error=lambda *args, **kwargs: None)
        return svc

    def test_find_dataset_by_name_prefers_direct_lookup(self):
        dataset = _DatasetObj("target-id", "Target Dataset")
        svc = self._build_service(_ClientWithGetDataset(dataset))

        found = svc._find_dataset_by_name("Target Dataset")

        self.assertIs(found, dataset)
        self.assertEqual(svc.client.calls, ["Target Dataset"])

    def test_find_dataset_by_name_uses_filtered_paged_list(self):
        page1 = [_DatasetObj("target-id", "Target Dataset")]
        client = _ClientWithPagedList({1: page1})
        svc = self._build_service(client)

        found = svc._find_dataset_by_name("Target Dataset")

        self.assertIs(found, page1[0])
        self.assertEqual(
            client.calls,
            [{"page": 1, "page_size": 200, "name": "Target Dataset"}],
        )


if __name__ == "__main__":
    unittest.main()
