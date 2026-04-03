import os
import tempfile
import unittest
from dataclasses import dataclass

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.knowledge.router import router as knowledge_router
from backend.database.schema.ensure import ensure_schema


@dataclass
class _Doc:
    doc_id: str
    kb_id: str
    file_path: str
    filename: str
    kb_name: str | None = None
    kb_dataset_id: str | None = None
    file_size: int = 0
    mime_type: str = "text/plain; charset=utf-8"
    uploaded_by: str = "u1"
    status: str = "approved"
    uploaded_at_ms: int = 0
    reviewed_by: str | None = None
    reviewed_at_ms: int | None = None
    review_notes: str | None = None
    ragflow_doc_id: str | None = None


class _User:
    def __init__(self):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = "viewer"
        self.status = "active"
        self.group_id = 1
        self.group_ids = [1]


class _UserStore:
    def __init__(self):
        self._user = _User()

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user

    def get_usernames_by_ids(self, user_ids):
        return {uid: f"user_{uid}" for uid in (user_ids or [])}


class _PermissionGroupStore:
    def get_group(self, group_id: int):
        if group_id == 1:
            return {
                "can_upload": False,
                "can_review": False,
                "can_download": True,
                "can_copy": False,
                "can_delete": False,
                "can_manage_kb_directory": False,
                "can_view_kb_config": False,
                "can_view_tools": False,
                "accessible_kbs": ["kb_allowed"],
                "accessible_chats": [],
                "accessible_tools": [],
            }
        return None


class _KbStore:
    def __init__(self, docs: list[_Doc], *, db_path: str):
        self._docs = {doc.doc_id: doc for doc in docs}
        self.db_path = db_path

    def list_documents(self, status=None, kb_refs=None, kb_id=None, uploaded_by=None, limit=100):  # noqa: ARG002
        docs = list(self._docs.values())
        if status is not None:
            docs = [doc for doc in docs if doc.status == status]
        if kb_refs:
            refs = set(kb_refs)
            docs = [
                doc
                for doc in docs
                if doc.kb_id in refs
                or (doc.kb_dataset_id is not None and doc.kb_dataset_id in refs)
                or (doc.kb_name is not None and doc.kb_name in refs)
            ]
        return docs[:limit]

    def get_document(self, doc_id: str):
        return self._docs.get(doc_id)


class _DownloadLogStore:
    def log_download(self, **kwargs):  # noqa: ARG002
        return None


class _RagflowService:
    def get_dataset_index(self):
        return {"by_id": {}, "by_name": {}}


class _Deps:
    def __init__(self, docs: list[_Doc], *, db_path: str):
        self.user_store = _UserStore()
        self.permission_group_store = _PermissionGroupStore()
        self.kb_store = _KbStore(docs, db_path=db_path)
        self.download_log_store = _DownloadLogStore()
        self.ragflow_service = _RagflowService()
        self.knowledge_directory_manager = None


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestKnowledgeVisibilityGuardUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        allowed_path = os.path.join(self._tmp.name, "allowed.txt")
        denied_path = os.path.join(self._tmp.name, "denied.txt")
        with open(allowed_path, "wb") as f:
            f.write(b"allowed")
        with open(denied_path, "wb") as f:
            f.write(b"denied")

        allowed_doc = _Doc(
            doc_id="doc_allowed",
            kb_id="kb_allowed",
            kb_name="kb_allowed",
            file_path=allowed_path,
            filename="allowed.txt",
            file_size=7,
        )
        denied_doc = _Doc(
            doc_id="doc_denied",
            kb_id="kb_denied",
            kb_name="kb_denied",
            file_path=denied_path,
            filename="denied.txt",
            file_size=6,
        )

        self._db_path = os.path.join(self._tmp.name, "auth.db")
        ensure_schema(self._db_path)

        app = FastAPI()
        app.state.deps = _Deps([allowed_doc, denied_doc], db_path=self._db_path)
        app.include_router(knowledge_router, prefix="/api/knowledge")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self._tmp.cleanup()

    def test_list_documents_filters_to_authorized_kb(self):
        resp = self.client.get("/api/knowledge/documents")
        self.assertEqual(resp.status_code, 200, resp.text)
        payload = resp.json()
        self.assertEqual(payload.get("count"), 1)
        self.assertEqual(payload.get("documents")[0].get("doc_id"), "doc_allowed")

    def test_list_documents_rejects_forbidden_kb_filter(self):
        resp = self.client.get("/api/knowledge/documents", params={"kb_id": "kb_denied"})
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "kb_not_allowed")

    def test_get_document_rejects_forbidden_kb_doc(self):
        resp = self.client.get("/api/knowledge/documents/doc_denied")
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "kb_not_allowed")

    def test_download_document_rejects_forbidden_kb_doc(self):
        resp = self.client.get("/api/knowledge/documents/doc_denied/download")
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "kb_not_allowed")

    def test_preview_document_rejects_forbidden_kb_doc(self):
        resp = self.client.get("/api/knowledge/documents/doc_denied/preview")
        self.assertEqual(resp.status_code, 403, resp.text)
        self.assertEqual(resp.json().get("detail"), "kb_not_allowed")


if __name__ == "__main__":
    unittest.main()
