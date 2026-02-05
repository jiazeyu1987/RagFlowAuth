import base64
import io
import os
import tempfile
import unittest
import uuid
import zipfile

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.core.config import settings
from backend.app.modules.documents.router import router as documents_router
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


class _NoopLogStore:
    def log_download(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None

    def log_deletion(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


class _KbDoc:
    def __init__(
        self,
        *,
        doc_id: str,
        kb_id: str,
        kb_name: str,
        kb_dataset_id: str | None,
        file_path: str,
        filename: str,
        file_size: int,
        mime_type: str,
        uploaded_by: str,
        status: str,
    ):
        self.doc_id = doc_id
        self.kb_id = kb_id
        self.kb_name = kb_name
        self.kb_dataset_id = kb_dataset_id
        self.file_path = file_path
        self.filename = filename
        self.file_size = file_size
        self.mime_type = mime_type
        self.uploaded_by = uploaded_by
        self.status = status
        self.uploaded_at_ms = 0
        self.reviewed_by = None
        self.reviewed_at_ms = None
        self.review_notes = None
        self.ragflow_doc_id = None


class _KbStore:
    def __init__(self):
        self._docs: dict[str, _KbDoc] = {}

    def create_document(
        self,
        *,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploaded_by: str,
        kb_id: str,
        kb_dataset_id: str | None,
        kb_name: str,
        status: str,
    ):
        doc_id = uuid.uuid4().hex
        doc = _KbDoc(
            doc_id=doc_id,
            kb_id=kb_id,
            kb_name=kb_name,
            kb_dataset_id=kb_dataset_id,
            file_path=file_path,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=uploaded_by,
            status=status,
        )
        self._docs[doc_id] = doc
        return doc

    def get_document(self, doc_id: str):
        return self._docs.get(doc_id)

    def delete_document(self, doc_id: str):
        self._docs.pop(doc_id, None)


class _RagflowService:
    def delete_document(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return True

    def download_document(self, doc_id: str, dataset: str):  # noqa: ARG002
        return b"%PDF-1.4 test", "r.pdf"


class _Deps:
    def __init__(self, kb_store: _KbStore, *, user: _User | None = None, permission_groups: dict[int, dict] | None = None):
        self.user_store = _UserStore(user or _User(role="admin"))
        self.kb_store = kb_store
        self.ragflow_service = _RagflowService()
        self.download_log_store = _NoopLogStore()
        self.deletion_log_store = _NoopLogStore()
        self.permission_group_store = _PermissionGroupStore(permission_groups or {})


class _PermissionGroupStore:
    def __init__(self, groups: dict[int, dict]):
        self._groups = groups

    def get_group(self, group_id: int):
        return self._groups.get(int(group_id))


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


def _make_docx_bytes(text: str) -> bytes:
    # Minimal docx that satisfies backend.services.docx_to_html_fallback:
    # it only requires `word/document.xml` inside the zip.
    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", xml.encode("utf-8"))
    return bio.getvalue()


def _make_xlsx_bytes() -> bytes:
    # Minimal xlsx-like zip. Preview requires LibreOffice; without it the backend
    # returns an `unsupported` payload with a readable message. The bytes must be
    # a file-like blob to exercise upload/download paths.
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", b'<?xml version="1.0" encoding="UTF-8"?>')
        zf.writestr("xl/workbook.xml", b'<?xml version="1.0" encoding="UTF-8"?>')
    return bio.getvalue()


class TestDocumentsPreviewGatewayE2E(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self._old_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = os.path.join(self._td.name, "uploads")

        self.kb_store = _KbStore()
        self.app = FastAPI()
        self.app.state.deps = _Deps(self.kb_store)
        self.app.include_router(documents_router, prefix="/api")
        self.app.include_router(preview_router, prefix="/api")
        self.app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        settings.UPLOAD_DIR = self._old_upload_dir
        self._td.cleanup()

    def _upload(self, filename: str, content: bytes, kb_id: str = "灞曞巺") -> dict:
        resp = self.client.post(
            f"/api/documents/knowledge/upload?kb_id={kb_id}",
            files={"file": (filename, content, "application/octet-stream")},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertTrue(data.get("doc_id"))
        return data

    def _preview(self, doc_id: str) -> dict:
        resp = self.client.get(f"/api/preview/documents/knowledge/{doc_id}/preview")
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def test_upload_preview_download_delete_for_multiple_filetypes(self):
        cases = [
            ("a.txt", b"hello-txt", "text", lambda d: self.assertEqual(d.get("content"), "hello-txt")),
            ("a.md", b"# Title\n\n- item\n", "text", lambda d: self.assertIn("# Title", d.get("content", ""))),
            ("a.csv", b"c1,c2\n1,2\n", "text", lambda d: self.assertIn("c1,c2", d.get("content", ""))),
            ("a.pdf", b"%PDF-1.4\n% test\n1 0 obj\n<<>>\nendobj\n%%EOF\n", "pdf", None),
            ("a.docx", _make_docx_bytes("hello-docx"), "html", None),
            ("a.xlsx", _make_xlsx_bytes(), "unsupported", None),
        ]

        uploaded: list[tuple[str, str, bytes]] = []
        for filename, content, expected_type, extra_assert in cases:
            up = self._upload(filename, content)
            doc_id = up["doc_id"]
            uploaded.append((doc_id, filename, content))

            pv = self._preview(doc_id)
            self.assertEqual(pv.get("type"), expected_type, pv)

            if expected_type == "pdf":
                raw = base64.b64decode(pv.get("content") or "")
                self.assertTrue(raw.startswith(b"%PDF"), "preview pdf bytes should start with %PDF")
            if expected_type == "html":
                raw = base64.b64decode(pv.get("content") or "")
                self.assertIn(b"<html", raw.lower())
            if expected_type == "unsupported":
                msg = str(pv.get("message") or "")
                self.assertIn("soffice", msg.lower())

            if callable(extra_assert):
                extra_assert(pv)

        # Download + delete should roundtrip on a knowledge document
        for doc_id, filename, original in uploaded:
            dl = self.client.get(f"/api/documents/knowledge/{doc_id}/download")
            self.assertEqual(dl.status_code, 200, dl.text)
            self.assertIn("Content-Disposition", dl.headers)
            self.assertIn(filename, dl.headers["Content-Disposition"])
            self.assertEqual(dl.content, original)

            del_resp = self.client.delete(f"/api/documents/knowledge/{doc_id}")
            self.assertEqual(del_resp.status_code, 200, del_resp.text)
            self.assertIsNone(self.kb_store.get_document(doc_id))

            # preview after deletion should be 404 (doc not found)
            pv2 = self.client.get(f"/api/preview/documents/knowledge/{doc_id}/preview")
            self.assertEqual(pv2.status_code, 404)

    def test_preview_allowed_without_download_permission_but_download_forbidden(self):
        # Non-admin user: can access KB but cannot download/delete/upload.
        user = _User(role="user")
        user.group_ids = [1]
        groups = {
            1: {
                "can_upload": False,
                "can_review": False,
                "can_download": False,
                "can_delete": False,
                "accessible_kbs": ["灞曞巺"],
                "accessible_chats": [],
            }
        }

        app = FastAPI()
        app.state.deps = _Deps(self.kb_store, user=user, permission_groups=groups)
        app.include_router(documents_router, prefix="/api")
        app.include_router(preview_router, prefix="/api")
        app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

        with TestClient(app) as client:
            # Create a local KB doc record + file directly (no upload permission).
            path = os.path.join(settings.UPLOAD_DIR, "p.txt")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"hello")
            doc = self.kb_store.create_document(
                filename="p.txt",
                file_path=path,
                file_size=5,
                mime_type="text/plain; charset=utf-8",
                uploaded_by="u1",
                kb_id="灞曞巺",
                kb_dataset_id=None,
                kb_name="灞曞巺",
                status="pending",
            )

            pv = client.get(f"/api/preview/documents/knowledge/{doc.doc_id}/preview")
            self.assertEqual(pv.status_code, 200, pv.text)
            self.assertEqual(pv.json().get("type"), "text")

            dl = client.get(f"/api/documents/knowledge/{doc.doc_id}/download")
            self.assertEqual(dl.status_code, 403)
            self.assertIn("no_download_permission", dl.text)

    def test_ragflow_preview_gateway_contract(self):
        # preview gateway ragflow branch should return the same contract (pdf base64).
        resp = self.client.get("/api/preview/documents/ragflow/r1/preview?dataset=灞曞巺")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data.get("type"), "pdf")
        self.assertEqual(data.get("filename"), "r.pdf")
        self.assertIn("content", data)
