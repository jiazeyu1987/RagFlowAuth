import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.ragflow.router import router as ragflow_router


class _User:
    def __init__(self):
        self.user_id = "u_admin"
        self.username = "admin"
        self.email = "admin@example.com"
        self.role = "admin"
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _UserStore:
    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _User()


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


_UNSET = object()


class _RagflowService:
    def __init__(self, *, list_payload=None, status_payload="running", detail_payload=_UNSET):
        self.list_payload = [] if list_payload is None else list_payload
        self.status_payload = status_payload
        self.detail_payload = (
            {
                "id": "doc-1",
                "name": "Doc 1",
                "status": "running",
                "dataset": "KB-1",
            }
            if detail_payload is _UNSET
            else detail_payload
        )

    def list_documents(self, dataset_name: str):  # noqa: ARG002
        return self.list_payload

    def normalize_dataset_id(self, kb_ref: str):
        return kb_ref

    def resolve_dataset_name(self, kb_ref: str):
        return kb_ref

    def download_document(self, doc_id: str, dataset_name: str):  # noqa: ARG002
        return b"hello", "doc.txt"

    def upload_document_blob(self, filename: str, content: bytes, kb_id: str):  # noqa: ARG002
        return "doc-target"

    def parse_document(self, dataset_ref: str, document_id: str):  # noqa: ARG002
        return True

    def get_document_status(self, doc_id: str, dataset_name: str):  # noqa: ARG002
        return self.status_payload

    def get_document_detail(self, doc_id: str, dataset_name: str):  # noqa: ARG002
        return self.detail_payload


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u_admin")


class TestRagflowDocumentsRoutesUnit(unittest.TestCase):
    def _make_client(self, ragflow_service=None) -> TestClient:
        app = FastAPI()
        app.state.deps = SimpleNamespace(
            user_store=_UserStore(),
            permission_group_store=_PermissionGroupStore(),
            ragflow_service=ragflow_service or _RagflowService(),
        )
        app.include_router(ragflow_router, prefix="/api/ragflow")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_list_documents_requires_dataset_name(self):
        with self._make_client() as client:
            resp = client.get("/api/ragflow/documents")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "missing_dataset_name")

    def test_list_documents_fails_fast_on_invalid_service_payload(self):
        with self._make_client(ragflow_service=_RagflowService(list_payload={"not": "a-list"})) as client:
            resp = client.get("/api/ragflow/documents?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "documents_invalid_payload")

    def test_status_returns_status_envelope(self):
        with self._make_client(ragflow_service=_RagflowService(status_payload="finished")) as client:
            resp = client.get("/api/ragflow/documents/doc-1/status?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": {"doc_id": "doc-1", "status": "finished"}})

    def test_status_fails_fast_on_invalid_service_payload(self):
        with self._make_client(ragflow_service=_RagflowService(status_payload={"state": "finished"})) as client:
            resp = client.get("/api/ragflow/documents/doc-1/status?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "document_status_invalid_payload")

    def test_status_returns_not_found_code(self):
        with self._make_client(ragflow_service=_RagflowService(status_payload=None)) as client:
            resp = client.get("/api/ragflow/documents/doc-1/status?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "document_not_found")

    def test_detail_returns_document_envelope(self):
        detail_payload = {
            "id": "doc-1",
            "name": "Doc 1",
            "status": "finished",
            "dataset": "KB-1",
        }
        with self._make_client(ragflow_service=_RagflowService(detail_payload=detail_payload)) as client:
            resp = client.get("/api/ragflow/documents/doc-1?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"document": detail_payload})

    def test_detail_fails_fast_on_invalid_service_payload(self):
        with self._make_client(ragflow_service=_RagflowService(detail_payload=["doc-1"])) as client:
            resp = client.get("/api/ragflow/documents/doc-1?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "document_detail_invalid_payload")

    def test_detail_returns_not_found_code(self):
        with self._make_client(ragflow_service=_RagflowService(detail_payload=None)) as client:
            resp = client.get("/api/ragflow/documents/doc-1?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "document_not_found")

    def test_delete_returns_result_envelope(self):
        with patch("backend.app.modules.ragflow.routes.documents.DocumentManager.delete_ragflow_document") as delete_mock:
            with self._make_client() as client:
                resp = client.delete("/api/ragflow/documents/doc-1?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"result": {"message": "document_deleted"}})
        delete_mock.assert_called_once()

    def test_download_requires_dataset(self):
        with self._make_client() as client:
            resp = client.get("/api/ragflow/documents/doc-1/download")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "missing_dataset")

    def test_delete_requires_dataset_name(self):
        with self._make_client() as client:
            resp = client.delete("/api/ragflow/documents/doc-1")

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "missing_dataset_name")

    def test_batch_download_requires_dataset_for_each_document(self):
        with self._make_client() as client:
            resp = client.post(
                "/api/ragflow/documents/batch/download",
                json={"documents": [{"doc_id": "doc-1", "name": "Doc 1"}]},
            )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "missing_dataset")

    def test_transfer_document_returns_result_envelope(self):
        with self._make_client() as client:
            resp = client.post(
                "/api/ragflow/documents/doc-1/transfer",
                json={
                    "source_dataset_name": "KB-1",
                    "target_dataset_name": "KB-2",
                    "operation": "copy",
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "result": {
                    "ok": True,
                    "operation": "copy",
                    "source_dataset_name": "KB-1",
                    "target_dataset_name": "KB-2",
                    "source_doc_id": "doc-1",
                    "target_doc_id": "doc-target",
                    "filename": "doc.txt",
                    "source_deleted": False,
                    "parse_triggered": True,
                    "parse_error": "",
                }
            },
        )

    def test_transfer_document_fails_fast_on_invalid_payload(self):
        with patch(
            "backend.app.modules.ragflow.routes.documents._transfer_one_document",
            return_value={"ok": True, "operation": "copy"},
        ):
            with self._make_client() as client:
                resp = client.post(
                    "/api/ragflow/documents/doc-1/transfer",
                    json={
                        "source_dataset_name": "KB-1",
                        "target_dataset_name": "KB-2",
                        "operation": "copy",
                    },
                )

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "ragflow_document_transfer_invalid_payload")

    def test_transfer_documents_batch_returns_result_envelope(self):
        with self._make_client() as client:
            resp = client.post(
                "/api/ragflow/documents/transfer/batch",
                json={
                    "operation": "copy",
                    "items": [
                        {
                            "doc_id": "doc-1",
                            "source_dataset_name": "KB-1",
                            "target_dataset_name": "KB-2",
                        }
                    ],
                },
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "result": {
                    "ok": True,
                    "operation": "copy",
                    "total": 1,
                    "success_count": 1,
                    "failed_count": 0,
                    "results": [
                        {
                            "ok": True,
                            "operation": "copy",
                            "source_dataset_name": "KB-1",
                            "target_dataset_name": "KB-2",
                            "source_doc_id": "doc-1",
                            "target_doc_id": "doc-target",
                            "filename": "doc.txt",
                            "source_deleted": False,
                            "parse_triggered": True,
                            "parse_error": "",
                        }
                    ],
                    "failed": [],
                }
            },
        )

    def test_transfer_documents_batch_fails_fast_on_invalid_payload(self):
        with patch(
            "backend.app.modules.ragflow.routes.documents._transfer_one_document",
            return_value={"ok": True, "operation": "copy"},
        ):
            with self._make_client() as client:
                resp = client.post(
                    "/api/ragflow/documents/transfer/batch",
                    json={
                        "operation": "copy",
                        "items": [
                            {
                                "doc_id": "doc-1",
                                "source_dataset_name": "KB-1",
                                "target_dataset_name": "KB-2",
                            }
                        ],
                    },
                )

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "ragflow_document_transfer_batch_invalid_payload")


if __name__ == "__main__":
    unittest.main()
