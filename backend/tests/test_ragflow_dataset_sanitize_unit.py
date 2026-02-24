import unittest

from backend.services.ragflow.mixins.datasets import RagflowDatasetsMixin


class _Svc(RagflowDatasetsMixin):
    pass


class TestRagflowDatasetSanitizeUnit(unittest.TestCase):
    def test_sanitizes_create_allowlist(self):
        svc = _Svc()
        cleaned = svc._sanitize_dataset_create_body(
            {
                "id": "x",
                "dataset_id": "y",
                "create_time": 1,
                "chunk_count": 2,
                "name": "A",
                "description": "B",
                "chunk_method": "naive",
                "embedding_model": "E",
                "avatar": None,
                "pagerank": 0,
                "status": 1,
            }
        )
        self.assertNotIn("id", cleaned)
        self.assertNotIn("dataset_id", cleaned)
        self.assertNotIn("create_time", cleaned)
        self.assertNotIn("chunk_count", cleaned)
        self.assertNotIn("pagerank", cleaned)
        self.assertNotIn("status", cleaned)
        self.assertEqual(cleaned.get("name"), "A")
        self.assertEqual(cleaned.get("description"), "B")
        self.assertEqual(cleaned.get("chunk_method"), "naive")
        self.assertEqual(cleaned.get("embedding_model"), "E")
        self.assertIn("avatar", cleaned)

    def test_sanitizes_update_allowlist(self):
        svc = _Svc()
        cleaned = svc._sanitize_dataset_update_body(
            {
                "name": "A",
                "pagerank": 0,
                "pipeline_id": "",
                "language": "English",
            }
        )
        self.assertEqual(cleaned.get("name"), "A")
        self.assertEqual(cleaned.get("pagerank"), 0)
        self.assertNotIn("pipeline_id", cleaned)
        self.assertNotIn("language", cleaned)


if __name__ == "__main__":
    unittest.main()
