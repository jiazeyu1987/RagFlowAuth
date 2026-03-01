import unittest
from types import SimpleNamespace

from backend.services.ragflow.mixins.documents import RagflowDocumentsMixin


class _DocObj:
    def __init__(self, doc_id: str, name: str, status: str = "ready"):
        self.id = doc_id
        self.name = name
        self.status = status


class _Dataset:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.id = "dataset-1"

    def list_documents(self, page=1, page_size=30, **kwargs):  # noqa: ARG002
        self.calls.append({"page": page, "page_size": page_size})
        return list(self.pages.get(page, []))


class _DatasetWithoutPaging:
    def __init__(self):
        self.id = "dataset-http-1"
        self.calls = 0

    def list_documents(self):
        self.calls += 1
        return []


class _HttpStub:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.config = SimpleNamespace(base_url="http://ragflow.local")

    def get_json(self, path, *, params=None):
        self.calls.append({"path": path, "params": dict(params or {})})
        if "id" in (params or {}):
            doc_id = (params or {}).get("id")
            docs = []
            for page_docs in self.pages.values():
                for doc in page_docs:
                    if isinstance(doc, dict) and doc.get("id") == doc_id:
                        docs.append(doc)
            return {"code": 0, "data": {"docs": docs[:1]}}
        page = int((params or {}).get("page", 1))
        return {"code": 0, "data": {"docs": list(self.pages.get(page, []))}}

    def headers(self):
        return {"Authorization": "Bearer test"}


class _Svc(RagflowDocumentsMixin):
    def __init__(self, dataset, http=None):
        self.client = object()
        self.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        self._dataset = dataset
        self._http = http or _HttpStub({})

    def _normalize_dataset_name_for_ops(self, dataset_name):
        return dataset_name

    def _find_dataset_by_name(self, dataset_name):  # noqa: ARG002
        return self._dataset


class TestRagflowDocumentsMixinUnit(unittest.TestCase):
    def test_list_documents_stops_after_partial_page(self):
        dataset = _Dataset(
            {
                1: [_DocObj("1", "a"), _DocObj("2", "b")],
            }
        )
        svc = _Svc(dataset)

        docs = svc.list_documents("展厅")

        self.assertEqual(
            docs,
            [
                {"id": "1", "name": "a", "status": "ready"},
                {"id": "2", "name": "b", "status": "ready"},
            ],
        )
        self.assertEqual(dataset.calls, [{"page": 1, "page_size": 200}])

    def test_list_documents_continues_when_page_full(self):
        page1 = [_DocObj(str(i), f"doc-{i}") for i in range(1, 201)]
        page2 = [_DocObj("201", "doc-201"), _DocObj("202", "doc-202")]
        dataset = _Dataset({1: page1, 2: page2})
        svc = _Svc(dataset)

        docs = svc.list_documents("展厅")

        self.assertEqual(len(docs), 202)
        self.assertEqual(dataset.calls, [{"page": 1, "page_size": 200}, {"page": 2, "page_size": 200}])

    def test_list_documents_falls_back_to_http_when_sdk_has_no_paging(self):
        dataset = _DatasetWithoutPaging()
        http = _HttpStub(
            {
                1: [{"id": "1", "name": "a", "status": "ready"}],
            }
        )
        svc = _Svc(dataset, http=http)

        docs = svc.list_documents("展厅")

        self.assertEqual(docs, [{"id": "1", "name": "a", "status": "ready"}])
        self.assertEqual(dataset.calls, 0)
        self.assertEqual(
            http.calls,
            [{"path": "/api/v1/datasets/dataset-http-1/documents", "params": {"page": 1, "page_size": 200}}],
        )

    def test_download_document_uses_http_lookup_by_id(self):
        dataset = _DatasetWithoutPaging()
        http = _HttpStub(
            {
                1: [{"id": "x-1", "name": "second-page.txt", "status": "ready"}],
            }
        )
        svc = _Svc(dataset, http=http)
        svc._download_document_via_http = lambda dataset_id, document_id: b"hello"  # noqa: ARG005

        content, filename = svc.download_document("x-1", "展厅")

        self.assertEqual(content, b"hello")
        self.assertEqual(filename, "second-page.txt")
        self.assertEqual(
            http.calls,
            [{"path": "/api/v1/datasets/dataset-http-1/documents", "params": {"id": "x-1", "page": 1, "page_size": 1}}],
        )


if __name__ == "__main__":
    unittest.main()
