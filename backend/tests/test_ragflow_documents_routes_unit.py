import unittest
from types import SimpleNamespace

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


class _RagflowService:
    def list_documents(self, dataset_name: str):  # noqa: ARG002
        return {"not": "a-list"}

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


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u_admin")


class TestRagflowDocumentsRoutesUnit(unittest.TestCase):
    def _make_client(self) -> TestClient:
        app = FastAPI()
        app.state.deps = SimpleNamespace(
            user_store=_UserStore(),
            permission_group_store=_PermissionGroupStore(),
            ragflow_service=_RagflowService(),
        )
        app.include_router(ragflow_router, prefix="/api/ragflow")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        return TestClient(app)

    def test_list_documents_fails_fast_on_invalid_service_payload(self):
        with self._make_client() as client:
            resp = client.get("/api/ragflow/documents?dataset_name=KB-1")

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "documents_invalid_payload")

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


if __name__ == "__main__":
    unittest.main()
