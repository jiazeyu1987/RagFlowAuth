import tempfile
import unittest
from pathlib import Path
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


class _SdkParseDoc:
    def __init__(self, doc_id: str, *, chunk_count: int = 0, progress: float = 0.0, run: str = "0"):
        self.id = doc_id
        self.name = f"{doc_id}.txt"
        self.status = "1"
        self.chunk_count = chunk_count
        self.progress = progress
        self.run = run


class _SdkParseDataset:
    def __init__(self, document_sequences: dict[str, list[object | None]]):
        self.document_sequences = {key: list(value) for key, value in document_sequences.items()}
        self.list_calls = []
        self.parse_calls = []
        self.id = "dataset-sdk-1"
        self.name = "SDK Dataset"

    def list_documents(self, id=None, page=1, page_size=30, **kwargs):  # noqa: ARG002
        self.list_calls.append({"id": id, "page": page, "page_size": page_size})
        sequence = self.document_sequences.get(str(id), [])
        if not sequence:
            return []
        current = sequence.pop(0)
        self.document_sequences[str(id)] = sequence
        if current is None:
            return []
        return [current]

    def async_parse_documents(self, document_ids):
        self.parse_calls.append(list(document_ids))


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


class _ParseHttpStub:
    def __init__(self, *, visibility_sequences=None, post_payloads=None):
        self.visibility_sequences = {key: list(value) for key, value in (visibility_sequences or {}).items()}
        self.post_payloads = list(post_payloads or [])
        self.lookup_calls = []
        self.post_calls = []
        self.config = SimpleNamespace(base_url="http://ragflow.local")

    def get_json(self, path, *, params=None):
        query = dict(params or {})
        self.lookup_calls.append({"path": path, "params": query})
        doc_id = str(query.get("id") or "").strip()
        if doc_id:
            sequence = self.visibility_sequences.get(doc_id, [True])
            visible = sequence.pop(0) if sequence else True
            self.visibility_sequences[doc_id] = sequence
            docs = [{"id": doc_id, "name": f"{doc_id}.txt", "status": "uploaded"}] if visible else []
            return {"code": 0, "data": {"docs": docs}}

        docs = []
        for current_doc_id, sequence in list(self.visibility_sequences.items()):
            visible = sequence.pop(0) if sequence else True
            self.visibility_sequences[current_doc_id] = sequence
            if visible:
                docs.append({"id": current_doc_id, "name": f"{current_doc_id}.txt", "status": "uploaded"})
        return {"code": 0, "data": {"docs": docs}}

    def post_json(self, path, *, body=None):
        self.post_calls.append({"path": path, "body": dict(body or {})})
        if self.post_payloads:
            return self.post_payloads.pop(0)
        return {"code": 0}

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


class _ParseSvc(RagflowDocumentsMixin):
    def __init__(self, http):
        self.client = None
        self._http = http
        self.list_calls = 0
        self.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        self._PARSE_DOCUMENT_READY_TIMEOUT_S = 0.05
        self._PARSE_DOCUMENT_READY_POLL_INTERVAL_S = 0.0

    def normalize_dataset_id(self, dataset_ref):
        return "dataset-http-1" if dataset_ref else None

    def list_documents(self, dataset_name="dataset-http-1"):  # noqa: ARG002
        self.list_calls += 1
        docs = []
        for current_doc_id, sequence in list(self._http.visibility_sequences.items()):
            visible = sequence.pop(0) if sequence else True
            self._http.visibility_sequences[current_doc_id] = sequence
            if visible:
                docs.append({"id": current_doc_id, "name": f"{current_doc_id}.txt", "status": "uploaded"})
        return docs


class _SdkParseSvc(RagflowDocumentsMixin):
    def __init__(self, dataset, http=None):
        self.client = object()
        self.dataset = dataset
        self._http = http or _ParseHttpStub()
        self.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        self._PARSE_DOCUMENT_READY_TIMEOUT_S = 1.0
        self._PARSE_DOCUMENT_READY_POLL_INTERVAL_S = 0.0

    def _normalize_dataset_name_for_ops(self, dataset_name):
        return dataset_name

    def normalize_dataset_id(self, dataset_ref):
        return self.dataset.id if dataset_ref else None

    def _find_dataset_by_name(self, dataset_name):  # noqa: ARG002
        return self.dataset


class _UploadSvc(RagflowDocumentsMixin):
    def __init__(self):
        self.client = object()
        self.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        self.upload_blob_calls = []

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "dataset-1") -> str:
        self.upload_blob_calls.append(
            {
                "file_filename": file_filename,
                "file_content": file_content,
                "kb_id": kb_id,
            }
        )
        return "uploaded-doc-1"


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

    def test_parse_documents_waits_until_document_visible(self):
        http = _ParseHttpStub(
            visibility_sequences={"doc-1": [False, True]},
            post_payloads=[{"code": 0}],
        )
        svc = _ParseSvc(http)

        ok = svc.parse_documents(dataset_ref="dataset-http-1", document_ids=["doc-1"])

        self.assertTrue(ok)
        self.assertEqual(svc.list_calls, 0)
        self.assertEqual(
            http.lookup_calls,
            [
                {"path": "/api/v1/datasets/dataset-http-1/documents", "params": {"page": 1, "page_size": 200}},
                {"path": "/api/v1/datasets/dataset-http-1/documents", "params": {"page": 1, "page_size": 200}},
            ],
        )
        self.assertEqual(
            http.post_calls,
            [{"path": "/api/v1/datasets/dataset-http-1/chunks", "body": {"document_ids": ["doc-1"]}}],
        )

    def test_parse_documents_retries_when_chunks_endpoint_is_not_ready(self):
        http = _ParseHttpStub(
            visibility_sequences={"doc-1": [True]},
            post_payloads=[
                {"code": 102, "message": "Documents not found"},
                {"code": 0},
            ],
        )
        svc = _ParseSvc(http)

        ok = svc.parse_documents(dataset_ref="dataset-http-1", document_ids=["doc-1"])

        self.assertTrue(ok)
        self.assertEqual(len(http.post_calls), 2)

    def test_parse_documents_fails_fast_when_document_never_becomes_visible(self):
        http = _ParseHttpStub(
            visibility_sequences={"doc-1": [False, False, False]},
            post_payloads=[{"code": 0}],
        )
        svc = _ParseSvc(http)
        svc._PARSE_DOCUMENT_READY_TIMEOUT_S = 0.0

        ok = svc.parse_documents(dataset_ref="dataset-http-1", document_ids=["doc-1"])

        self.assertFalse(ok)
        self.assertEqual(http.post_calls, [])

    def test_parse_documents_prefers_http_chunks_flow_when_dataset_id_is_available(self):
        dataset = _SdkParseDataset(
            {
                "doc-1": [
                    None,
                    _SdkParseDoc("doc-1", chunk_count=0, progress=0.2, run="0"),
                    _SdkParseDoc("doc-1", chunk_count=1, progress=1.0, run="DONE"),
                ]
            }
        )
        http = _ParseHttpStub(
            visibility_sequences={"doc-1": [False, True]},
            post_payloads=[{"code": 0}],
        )
        svc = _SdkParseSvc(dataset, http=http)

        ok = svc.parse_documents(dataset_ref="dataset-sdk-1", document_ids=["doc-1"])

        self.assertTrue(ok)
        self.assertEqual(dataset.parse_calls, [])
        self.assertEqual(
            http.post_calls,
            [{"path": "/api/v1/datasets/dataset-sdk-1/chunks", "body": {"document_ids": ["doc-1"]}}],
        )

    def test_parse_documents_prefers_http_even_when_sdk_client_exists(self):
        dataset = _SdkParseDataset({"doc-1": [None, None, None]})
        http = _ParseHttpStub(
            visibility_sequences={"doc-1": [False, True]},
            post_payloads=[{"code": 0}],
        )
        svc = _SdkParseSvc(dataset, http=http)

        ok = svc.parse_documents(dataset_ref="dataset-sdk-1", document_ids=["doc-1"])

        self.assertTrue(ok)
        self.assertEqual(dataset.parse_calls, [])
        self.assertEqual(
            http.post_calls,
            [{"path": "/api/v1/datasets/dataset-sdk-1/chunks", "body": {"document_ids": ["doc-1"]}}],
        )

    def test_upload_document_reads_file_and_uses_blob_upload_path(self):
        svc = _UploadSvc()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "seed.txt"
            file_path.write_text("seed content\n", encoding="utf-8")
            expected_bytes = file_path.read_bytes()

            doc_id = svc.upload_document(str(file_path), kb_id="dataset-1")

        self.assertEqual(doc_id, "uploaded-doc-1")
        self.assertEqual(
            svc.upload_blob_calls,
            [
                {
                    "file_filename": "seed.txt",
                    "file_content": expected_bytes,
                    "kb_id": "dataset-1",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
