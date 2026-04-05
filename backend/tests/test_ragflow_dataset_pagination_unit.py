import unittest
from types import SimpleNamespace

from backend.services.ragflow.mixins.datasets import RagflowDatasetsMixin


class _DatasetObj:
    def __init__(self, dataset_id: str, name: str):
        self.id = dataset_id
        self.name = name
        self.document_count = 0
        self.chunk_count = 0
        self.description = None


class _SdkClient:
    def __init__(self, pages: dict[int, list[object]]):
        self.pages = pages
        self.calls: list[dict[str, int]] = []

    def list_datasets(self, page: int = 1, page_size: int = 30, **kwargs):  # noqa: ARG002
        self.calls.append({"page": page, "page_size": page_size})
        return list(self.pages.get(page, []))


class _HttpStub:
    def __init__(self, pages: dict[int, list[dict]]):
        self.pages = pages
        self.calls: list[dict[str, object]] = []
        self.config = SimpleNamespace(base_url="http://ragflow.local")

    def get_json(self, path: str, *, params=None):
        self.calls.append({"path": path, "params": dict(params or {})})
        page = int((params or {}).get("page", 1))
        return {"code": 0, "data": list(self.pages.get(page, []))}


class _Svc(RagflowDatasetsMixin):
    def __init__(self, *, client=None, http=None):
        self.client = client
        self._http = http
        self.config = {"api_key": "NOT_PLACEHOLDER"}
        self.logger = SimpleNamespace(
            error=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        )
        self._dataset_index_cache = None
        self._dataset_index_cache_at_s = 0.0

    def _reload_config_if_changed(self):
        return None


class TestRagflowDatasetPaginationUnit(unittest.TestCase):
    def test_list_datasets_pages_through_sdk_results(self):
        page1 = [_DatasetObj(f"ds-{index}", f"Dataset {index}") for index in range(1, 201)]
        page2 = [_DatasetObj("ds-201", "Dataset 201"), _DatasetObj("ds-202", "Dataset 202")]
        svc = _Svc(client=_SdkClient({1: page1, 2: page2}))

        datasets = svc.list_datasets()

        self.assertEqual(len(datasets), 202)
        self.assertEqual(datasets[-1]["id"], "ds-202")
        self.assertEqual(
            svc.client.calls,
            [{"page": 1, "page_size": 200}, {"page": 2, "page_size": 200}],
        )

    def test_list_datasets_pages_through_http_results(self):
        page1 = [{"id": f"ds-{index}", "name": f"Dataset {index}"} for index in range(1, 201)]
        page2 = [{"id": "ds-201", "name": "Dataset 201"}]
        http = _HttpStub({1: page1, 2: page2})
        svc = _Svc(http=http)

        datasets = svc.list_datasets()

        self.assertEqual(len(datasets), 201)
        self.assertEqual(datasets[-1]["id"], "ds-201")
        self.assertEqual(
            http.calls,
            [
                {"path": "/api/v1/datasets", "params": {"page": 1, "page_size": 200}},
                {"path": "/api/v1/datasets", "params": {"page": 2, "page_size": 200}},
            ],
        )

    def test_get_dataset_detail_finds_dataset_on_later_page(self):
        page1 = [{"id": f"ds-{index}", "name": f"Dataset {index}"} for index in range(1, 201)]
        page2 = [{"id": "target-ds", "name": "Target Dataset", "chunk_method": "naive"}]
        svc = _Svc(http=_HttpStub({1: page1, 2: page2}))

        detail = svc.get_dataset_detail("target-ds")

        self.assertIsInstance(detail, dict)
        self.assertEqual(detail.get("name"), "Target Dataset")


if __name__ == "__main__":
    unittest.main()
