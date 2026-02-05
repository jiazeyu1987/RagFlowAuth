import os
import tempfile
import unittest

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.preview.router import router as preview_router


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


class _KbStore:
    def __init__(self, doc: _KbDoc):
        self._doc = doc

    def get_document(self, doc_id: str):
        if doc_id == self._doc.doc_id:
            return self._doc
        return None


class _RagflowService:
    def __init__(self, content: bytes, filename: str):
        self._content = content
        self._filename = filename

    def download_document(self, doc_id: str, dataset: str):  # noqa: ARG002
        return self._content, self._filename


class _Deps:
    def __init__(self, kb_doc: _KbDoc):
        self.user_store = _UserStore(_User(role="admin"))
        self.kb_store = _KbStore(kb_doc)
        self.ragflow_service = _RagflowService(b"%PDF-1.4 test", "x.pdf")


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestPreviewGatewayUnit(unittest.TestCase):
    def test_gateway_knowledge_returns_json_contract(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "a.txt")
            with open(path, "wb") as f:
                f.write("hello".encode("utf-8"))

            kb_doc = _KbDoc(doc_id="k1", kb_id="展厅", file_path=path, filename="a.txt")

            app = FastAPI()
            app.state.deps = _Deps(kb_doc)
            app.include_router(preview_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/preview/documents/knowledge/k1/preview")

            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("type"), "text")
            self.assertEqual(data.get("filename"), "a.txt")
            self.assertIn("content", data)

    def test_gateway_ragflow_returns_json_contract(self):
        app = FastAPI()
        kb_doc = _KbDoc(doc_id="k1", kb_id="展厅", file_path=__file__, filename="a.txt")
        app.state.deps = _Deps(kb_doc)
        app.include_router(preview_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            resp = client.get("/api/preview/documents/ragflow/r1/preview?dataset=展厅")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("type"), "pdf")
        self.assertEqual(data.get("filename"), "x.pdf")
        self.assertIn("content", data)

