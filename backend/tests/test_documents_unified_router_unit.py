import io
import os
import unittest
import zipfile

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.documents.router import router as documents_router
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, role: str = "admin"):
        self.user_id = "u1"
        self.username = "u1"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _KbDoc:
    def __init__(self, doc_id: str, kb_id: str, file_path: str, filename: str):
        self.doc_id = doc_id
        self.kb_id = kb_id
        self.file_path = file_path
        self.filename = filename
        self.file_size = os.path.getsize(file_path)
        self.mime_type = "text/plain; charset=utf-8"
        self.uploaded_by = "u1"
        self.status = "approved"
        self.uploaded_at_ms = 0
        self.reviewed_by = None
        self.reviewed_at_ms = None
        self.review_notes = None
        self.ragflow_doc_id = None
        self.kb_dataset_id = None
        self.kb_name = kb_id


class _KbStore:
    def __init__(self, doc: _KbDoc):
        self._doc = doc

    def get_document(self, doc_id: str):
        if doc_id == self._doc.doc_id:
            return self._doc
        return None

    def delete_document(self, doc_id: str):  # noqa: ARG002
        return True


class _RagflowService:
    def download_document(self, doc_id: str, dataset: str):  # noqa: ARG002
        return b"hello", "a.txt"

    def delete_document(self, document_id: str, dataset_name: str = "kb1"):  # noqa: ARG002
        return True

    def batch_download_documents(self, documents_info):  # noqa: ARG002
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("a.txt", b"hello")
        return buf.getvalue(), "ragflow_docs.zip"


class _DownloadLogStore:
    def log_download(self, **kwargs):  # noqa: ARG002
        return None


class _DeletionLogStore:
    def log_deletion(self, **kwargs):  # noqa: ARG002
        return None


class _Deps:
    def __init__(self, kb_doc: _KbDoc):
        self.user_store = _UserStore(_User(role="admin"))
        self.kb_store = _KbStore(kb_doc)
        self.ragflow_service = _RagflowService()
        self.download_log_store = _DownloadLogStore()
        self.deletion_log_store = _DeletionLogStore()


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestDocumentsUnifiedRouterUnit(unittest.TestCase):
    def test_unified_download_knowledge(self):
        td = make_temp_dir(prefix="ragflowauth_documents_router")
        try:
            path = os.path.join(str(td), "a.txt")
            with open(path, "wb") as f:
                f.write(b"hello")

            kb_doc = _KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="a.txt")
            app = FastAPI()
            app.state.deps = _Deps(kb_doc)
            app.include_router(documents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/documents/knowledge/k1/download")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, b"hello")
        finally:
            cleanup_dir(td)

    def test_unified_download_ragflow(self):
        td = make_temp_dir(prefix="ragflowauth_documents_router")
        try:
            path = os.path.join(str(td), "x.txt")
            with open(path, "wb") as f:
                f.write(b"x")

            kb_doc = _KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="x.txt")
            app = FastAPI()
            app.state.deps = _Deps(kb_doc)
            app.include_router(documents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/documents/ragflow/r1/download?dataset=kb1")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, b"hello")
            self.assertIn("Content-Disposition", resp.headers)
        finally:
            cleanup_dir(td)

    def test_unified_batch_download_knowledge(self):
        td = make_temp_dir(prefix="ragflowauth_documents_router")
        try:
            path = os.path.join(str(td), "a.txt")
            with open(path, "wb") as f:
                f.write(b"hello")

            kb_doc = _KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="a.txt")
            app = FastAPI()
            app.state.deps = _Deps(kb_doc)
            app.include_router(documents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post("/api/documents/knowledge/batch/download", json={"doc_ids": ["k1"]})

            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.headers.get("Content-Type"), "application/zip")
            with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
                self.assertIn("a.txt", zf.namelist())
                self.assertEqual(zf.read("a.txt"), b"hello")
        finally:
            cleanup_dir(td)

    def test_unified_batch_download_ragflow(self):
        td = make_temp_dir(prefix="ragflowauth_documents_router")
        try:
            path = os.path.join(str(td), "a.txt")
            with open(path, "wb") as f:
                f.write(b"hello")

            kb_doc = _KbDoc(doc_id="k1", kb_id="ds1", file_path=path, filename="a.txt")
            app = FastAPI()
            app.state.deps = _Deps(kb_doc)
            app.include_router(documents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post(
                    "/api/documents/ragflow/batch/download",
                    json={"documents": [{"doc_id": "r1", "name": "a.txt", "dataset": "ds1"}]},
                )

            self.assertEqual(resp.status_code, 200, resp.text)
            self.assertEqual(resp.headers.get("Content-Type"), "application/zip")
            self.assertIn("Content-Disposition", resp.headers)
            with zipfile.ZipFile(io.BytesIO(resp.content), "r") as zf:
                self.assertIn("a.txt", zf.namelist())
                self.assertEqual(zf.read("a.txt"), b"hello")
        finally:
            cleanup_dir(td)
