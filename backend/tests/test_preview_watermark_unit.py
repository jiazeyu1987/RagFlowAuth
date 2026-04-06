import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.onlyoffice.router import router as onlyoffice_router
from backend.app.modules.preview.router import router as preview_router
from backend.services.onlyoffice_security import parse_file_access_token
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self):
        self.user_id = "u1"
        self.username = "u1"
        self.full_name = "测试用户"
        self.email = "u1@example.com"
        self.role = "viewer"
        self.status = "active"
        self.company_id = 1
        self.group_id = 1
        self.group_ids = [1]


class _UserStore:
    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return _User()


class _KbDoc:
    def __init__(self, doc_id: str, kb_id: str, file_path: str, filename: str):
        self.doc_id = doc_id
        self.kb_id = kb_id
        self.file_path = file_path
        self.filename = filename
        self.mime_type = "text/plain; charset=utf-8"
        self.kb_name = kb_id
        self.kb_dataset_id = None


class _KbStore:
    def __init__(self, doc: _KbDoc):
        self._doc = doc

    def get_document(self, doc_id: str):
        if doc_id == self._doc.doc_id:
            return self._doc
        return None


class _PermissionGroupStore:
    def get_group(self, group_id: int):
        if group_id != 1:
            return None
        return {
            "can_upload": False,
            "can_review": False,
            "can_download": True,
            "can_copy": False,
            "can_delete": False,
            "can_manage_kb_directory": False,
            "can_view_kb_config": False,
            "can_view_tools": False,
            "accessible_kbs": ["kb1"],
            "accessible_chats": [],
            "accessible_tools": [],
        }


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
    def __init__(self, doc: _KbDoc):
        self.user_store = _UserStore()
        self.kb_store = _KbStore(doc)
        self.permission_group_store = _PermissionGroupStore()
        self.org_directory_store = _OrgDirectoryStore()
        self.org_structure_manager = self.org_directory_store
        self.watermark_policy_store = _WatermarkPolicyStore()
        self.knowledge_directory_manager = None


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestPreviewWatermarkUnit(unittest.TestCase):
    def test_preview_gateway_returns_backend_generated_watermark(self):
        td = make_temp_dir(prefix="ragflowauth_preview_watermark")
        try:
            path = os.path.join(str(td), "a.txt")
            with open(path, "wb") as f:
                f.write("hello watermark".encode("utf-8"))

            app = FastAPI()
            app.state.deps = _Deps(_KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="a.txt"))
            app.include_router(preview_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/preview/documents/knowledge/k1/preview")

            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            watermark = data.get("watermark") or {}
            self.assertEqual(watermark.get("policy_id"), "wm-default")
            self.assertIn("用户:测试用户", watermark.get("text", ""))
            self.assertIn("公司:测试公司", watermark.get("text", ""))
            self.assertIn("用途:预览", watermark.get("text", ""))
            self.assertIn("文档ID:k1", watermark.get("text", ""))
            self.assertEqual(watermark.get("actor_name"), _User().full_name)
            self.assertEqual(watermark.get("actor_account"), _User().username)
            self.assertEqual(watermark.get("overlay", {}).get("rotation_deg"), -24)
        finally:
            cleanup_dir(td)

    @patch("backend.app.modules.onlyoffice.router.settings.ONLYOFFICE_ENABLED", True)
    @patch("backend.app.modules.onlyoffice.router.settings.ONLYOFFICE_SERVER_URL", "http://onlyoffice.local")
    @patch("backend.app.modules.onlyoffice.router.settings.ONLYOFFICE_PUBLIC_API_BASE_URL", "")
    @patch("backend.app.modules.onlyoffice.router.settings.ONLYOFFICE_JWT_SECRET", "")
    @patch("backend.app.modules.onlyoffice.router.settings.ONLYOFFICE_FILE_TOKEN_TTL_SECONDS", 300)
    @patch("backend.services.onlyoffice_security.settings.ONLYOFFICE_FILE_TOKEN_SECRET", "unit-test-secret")
    def test_onlyoffice_editor_config_contains_watermark_and_token_claims(self):
        td = make_temp_dir(prefix="ragflowauth_onlyoffice_watermark")
        try:
            path = os.path.join(str(td), "report.docx")
            with open(path, "wb") as f:
                f.write(b"docx-placeholder")

            app = FastAPI()
            app.state.deps = _Deps(_KbDoc(doc_id="k1", kb_id="kb1", file_path=path, filename="report.docx"))
            app.include_router(onlyoffice_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.post(
                    "/api/onlyoffice/editor-config",
                    json={"source": "knowledge", "doc_id": "k1", "filename": "report.docx"},
                )

            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertEqual(data.get("watermark_policy_id"), "wm-default")
            self.assertIn("用途:预览", data.get("watermark_text", ""))
            self.assertIn("文档ID:k1", data.get("watermark_text", ""))

            file_url = data.get("config", {}).get("document", {}).get("url", "")
            token = parse_qs(urlparse(file_url).query).get("token", [""])[0]
            claims = parse_file_access_token(token)
            self.assertEqual(claims.get("watermark_policy_id"), "wm-default")
            self.assertEqual(claims.get("watermark_text"), data.get("watermark_text"))
        finally:
            cleanup_dir(td)
