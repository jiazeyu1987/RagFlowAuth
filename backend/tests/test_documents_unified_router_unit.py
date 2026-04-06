import io
import os
import unittest
import zipfile
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.documents.router import router as documents_router
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, role: str = "viewer", group_ids: list[int] | None = None):
        self.user_id = "u1"
        self.username = "u1"
        self.full_name = "测试用户"
        self.email = "u1@example.com"
        self.role = role
        self.status = "active"
        self.company_id = 1
        self.group_id = None
        self.group_ids = list(group_ids or [])


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


class _OperationApprovalService:
    def __init__(self):
        self.calls = []

    async def create_request(self, *, operation_type, ctx, **kwargs):
        self.calls.append(
            {
                "operation_type": operation_type,
                "actor": ctx.payload.sub,
                **dict(kwargs or {}),
            }
        )
        target_ref = str(kwargs.get("doc_id") or kwargs.get("kb_ref") or "")
        target_label = ""
        upload_file = kwargs.get("upload_file")
        if upload_file is not None:
            target_label = getattr(upload_file, "filename", "") or ""
        return {
            "request_id": "req-1",
            "operation_type": operation_type,
            "operation_label": operation_type,
            "status": "in_approval",
            "current_step_no": 1,
            "current_step_name": "review",
            "submitted_at_ms": 1,
            "target_ref": target_ref,
            "target_label": target_label,
            "applicant_user_id": ctx.payload.sub,
            "applicant_username": "u1",
            "summary": {},
            "last_error": None,
        }


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
                "accessible_kbs": ["kb1", "ds1"],
                "accessible_chats": [],
                "accessible_tools": [],
            }
        return None


class _Company:
    def __init__(self, name: str = "测试公司"):
        self.name = name


class _OrgDirectoryStore:
    def get_company(self, company_id: int):
        if company_id == 1:
            return _Company()
        return None


class _WatermarkPolicy:
    policy_id = "wm-default"
    name = "默认水印策略"
    text_template = "用户:{username} | 公司:{company} | 时间:{timestamp} | 用途:{purpose} | 文档ID:{doc_id}"
    label_text = "受控预览"
    text_color = "#6b7280"
    opacity = 0.18
    rotation_deg = -24
    gap_x = 260
    gap_y = 180
    font_size = 18


class _WatermarkPolicyStore:
    def get_active_policy(self):
        return _WatermarkPolicy()


class _Deps:
    def __init__(self, kb_doc: _KbDoc):
        self.user_store = _UserStore(_User(role="viewer", group_ids=[1]))
        self.kb_store = _KbStore(kb_doc)
        self.ragflow_service = _RagflowService()
        self.download_log_store = _DownloadLogStore()
        self.deletion_log_store = _DeletionLogStore()
        self.permission_group_store = _PermissionGroupStore()
        self.org_directory_store = _OrgDirectoryStore()
        self.org_structure_manager = self.org_directory_store
        self.watermark_policy_store = _WatermarkPolicyStore()
        self.operation_approval_service = _OperationApprovalService()


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
            self.assertEqual(resp.headers.get("X-Distribution-Mode"), "inline_text_watermark")
            self.assertEqual(resp.headers.get("X-Watermark-Policy-Id"), "wm-default")
            text = resp.content.decode("utf-8")
            self.assertIn("[受控分发水印]", text)
            self.assertIn("用途:下载", text)
            self.assertIn("文档ID:k1", text)
            self.assertIn("hello", text)
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
            self.assertEqual(resp.headers.get("X-Distribution-Mode"), "inline_text_watermark")
            text = resp.content.decode("utf-8")
            self.assertIn("用途:下载", text)
            self.assertIn("文档ID:r1", text)
            self.assertIn("hello", text)
            self.assertIn("Content-Disposition", resp.headers)
        finally:
            cleanup_dir(td)

    def test_unified_download_ragflow_requires_dataset(self):
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
                resp = client.get("/api/documents/ragflow/r1/download")

            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json()["detail"], "missing_dataset")
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
                self.assertIn("00_CONTROLLED_DISTRIBUTION.txt", zf.namelist())
                self.assertIn("watermark_manifest.json", zf.namelist())
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
            deps = _Deps(kb_doc)
            deps.user_store = _UserStore(_User(role="admin"))
            app.state.deps = deps
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
                self.assertIn("00_CONTROLLED_DISTRIBUTION.txt", zf.namelist())
                self.assertIn("watermark_manifest.json", zf.namelist())
                self.assertIn("a.txt", zf.namelist())
                self.assertEqual(zf.read("a.txt"), b"hello")
        finally:
            cleanup_dir(td)

    def test_unified_upload_knowledge_returns_request_envelope(self):
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
                resp = client.post(
                    "/api/documents/knowledge/upload?kb_id=kb1",
                    files={"file": ("demo.txt", b"hello", "text/plain")},
                )

            self.assertEqual(resp.status_code, 202, resp.text)
            self.assertEqual(resp.json()["request"]["request_id"], "req-1")
            self.assertEqual(resp.json()["request"]["operation_type"], "knowledge_file_upload")
        finally:
            cleanup_dir(td)

    def test_unified_upload_knowledge_requires_kb_id(self):
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
                resp = client.post(
                    "/api/documents/knowledge/upload",
                    files={"file": ("demo.txt", b"hello", "text/plain")},
                )

            self.assertEqual(resp.status_code, 400, resp.text)
            self.assertEqual(resp.json()["detail"], "missing_kb_id")
        finally:
            cleanup_dir(td)

    def test_unified_delete_knowledge_returns_request_envelope(self):
        td = make_temp_dir(prefix="ragflowauth_documents_router")
        try:
            path = os.path.join(str(td), "a.txt")
            with open(path, "wb") as f:
                f.write(b"hello")

            kb_doc = _KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="a.txt")
            app = FastAPI()
            deps = _Deps(kb_doc)
            app.state.deps = deps
            app.include_router(documents_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.delete("/api/documents/knowledge/k1")

            self.assertEqual(resp.status_code, 202, resp.text)
            self.assertEqual(resp.json()["request"]["request_id"], "req-1")
            self.assertEqual(
                deps.operation_approval_service.calls,
                [
                    {
                        "operation_type": "knowledge_file_delete",
                        "actor": "u1",
                        "doc_id": "k1",
                    }
                ],
            )
        finally:
            cleanup_dir(td)

    def test_unified_delete_ragflow_returns_result_envelope(self):
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

            with patch("backend.app.modules.documents.router.DocumentManager.delete_ragflow_document") as delete_mock:
                with TestClient(app) as client:
                    resp = client.delete("/api/documents/ragflow/r1?dataset_name=ds1")

            self.assertEqual(resp.status_code, 202, resp.text)
            self.assertEqual(resp.json(), {"result": {"message": "document_deleted"}})
            delete_mock.assert_called_once()
        finally:
            cleanup_dir(td)

    def test_unified_delete_ragflow_requires_dataset_name(self):
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
                resp = client.delete("/api/documents/ragflow/r1")

            self.assertEqual(resp.status_code, 400, resp.text)
            self.assertEqual(resp.json()["detail"], "missing_dataset_name")
        finally:
            cleanup_dir(td)
