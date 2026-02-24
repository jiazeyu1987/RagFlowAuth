import unittest

from backend.services.ragflow.mixins.datasets import RagflowDatasetsMixin


class _StubHttp:
    def __init__(self, datasets: list[dict]):
        self._datasets = datasets
        self.calls: list[tuple[str, str]] = []

    def get_list(self, path: str, *, params=None, context: str, data_field: str = "data", ok_code: int = 0):
        self.calls.append(("get_list", path))
        return list(self._datasets)


class _StubSvc(RagflowDatasetsMixin):
    def __init__(self, datasets: list[dict]):
        self._http = _StubHttp(datasets)
        self.config = {"api_key": "NOT_PLACEHOLDER"}
        self.client = None
        self.logger = None
        self._dataset_index_cache = None
        self._dataset_index_cache_at_s = 0.0

    def _reload_config_if_changed(self):
        return None


class TestRagflowDatasetDetailUnit(unittest.TestCase):
    def test_detail_is_found_via_list_endpoint(self):
        ds_id = "ds1"
        svc = _StubSvc([{"id": ds_id, "name": "A", "chunk_method": "naive"}, {"id": "ds2", "name": "B"}])
        out = svc.get_dataset_detail(ds_id)
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("id"), ds_id)
        self.assertIn(("get_list", "/api/v1/datasets"), svc._http.calls)

    def test_detail_falls_back_when_normalize_misses(self):
        ds_id = "ds1"

        class _Svc(_StubSvc):
            def normalize_dataset_id(self, ref: str):
                return None

        svc = _Svc([{"id": ds_id, "name": "A", "chunk_method": "naive"}])
        out = svc.get_dataset_detail(ds_id)
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("id"), ds_id)

    def test_detail_can_match_by_name_when_called_with_name(self):
        svc = _StubSvc([{"id": "ds1", "name": "MyKB", "chunk_method": "naive"}])
        out = svc.get_dataset_detail("MyKB")
        self.assertIsInstance(out, dict)
        self.assertEqual(out.get("id"), "ds1")

    def test_detail_returns_none_when_missing(self):
        svc = _StubSvc([{"id": "ds2", "name": "B"}])
        out = svc.get_dataset_detail("ds1")
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
