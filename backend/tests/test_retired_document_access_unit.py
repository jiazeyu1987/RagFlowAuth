import hashlib
import io
import os
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.audit.router import router as audit_router
from backend.app.modules.knowledge.router import router as knowledge_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.services.compliance import RetiredRecordsService
from backend.services.kb import KbStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self, *, user_id: str, role: str, group_ids: list[int]):
        self.user_id = user_id
        self.username = user_id
        self.email = f"{user_id}@example.com"
        self.role = role
        self.status = "active"
        self.group_id = group_ids[0] if group_ids else None
        self.group_ids = list(group_ids)
        self.company_id = 1
        self.department_id = 2


class _UserStore:
    def __init__(self, users: dict[str, _User]):
        self._users = users

    def get_by_user_id(self, user_id: str):
        return self._users.get(user_id)

    def get_usernames_by_ids(self, user_ids):
        return {user_id: self._users[user_id].username for user_id in user_ids if user_id in self._users}


class _PermissionGroupStore:
    def get_group(self, group_id: int):
        if group_id == 1:
            return {
                "can_upload": False,
                "can_review": True,
                "can_download": True,
                "can_copy": False,
                "can_delete": False,
                "can_manage_kb_directory": False,
                "can_view_kb_config": False,
                "can_view_tools": False,
                "accessible_kbs": ["kb-a"],
                "accessible_chats": [],
                "accessible_tools": [],
            }
        if group_id == 2:
            return {
                "can_upload": False,
                "can_review": False,
                "can_download": True,
                "can_copy": False,
                "can_delete": False,
                "can_manage_kb_directory": False,
                "can_view_kb_config": False,
                "can_view_tools": False,
                "accessible_kbs": [],
                "accessible_chats": [],
                "accessible_tools": [],
            }
        return None


class _DownloadLogStore:
    def log_download(self, **_kwargs):
        return None


class _OrgDirectoryStore:
    def get_company(self, company_id: int):  # noqa: ARG002
        return SimpleNamespace(name="Acme")

    def get_department(self, department_id: int):  # noqa: ARG002
        return SimpleNamespace(name="QA")


class _RagflowService:
    def get_dataset_index(self):
        return {"by_id": {}, "by_name": {}}


class _WatermarkPolicy:
    policy_id = "wm-retired"
    name = "Retired documents watermark"
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
    def __init__(self, *, db_path: str, users: dict[str, _User]):
        self.user_store = _UserStore(users)
        self.permission_group_store = _PermissionGroupStore()
        self.kb_store = KbStore(db_path=db_path)
        self.download_log_store = _DownloadLogStore()
        self.audit_log_store = AuditLogStore(db_path=db_path)
        self.audit_log_manager = AuditLogManager(store=self.audit_log_store)
        self.org_directory_store = _OrgDirectoryStore()
        self.org_structure_manager = self.org_directory_store
        self.watermark_policy_store = _WatermarkPolicyStore()
        self.ragflow_service = _RagflowService()
        self.knowledge_directory_manager = None


def _build_app(*, current_user_id: str, deps: _Deps) -> FastAPI:
    def _override_get_current_payload(_: Request) -> TokenPayload:
        return TokenPayload(sub=current_user_id)

    app = FastAPI()
    app.state.deps = deps
    app.include_router(knowledge_router, prefix="/api/knowledge")
    app.include_router(audit_router, prefix="/api")
    app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload
    return app


class TestRetiredDocumentAccessUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_retired_records")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.users = {
            "reviewer-1": _User(user_id="reviewer-1", role="reviewer", group_ids=[1]),
            "viewer-1": _User(user_id="viewer-1", role="viewer", group_ids=[2]),
            "admin-1": _User(user_id="admin-1", role="admin", group_ids=[]),
        }
        self.deps = _Deps(db_path=self.db_path, users=self.users)

        doc_path = Path(self._tmp) / "retire_me.txt"
        doc_path.write_text("retire me", encoding="utf-8")
        doc = self.deps.kb_store.create_document(
            filename="retire_me.txt",
            file_path=str(doc_path),
            file_size=doc_path.stat().st_size,
            mime_type="text/plain; charset=utf-8",
            uploaded_by="reviewer-1",
            kb_id="kb-a",
            kb_dataset_id="ds-a",
            kb_name="kb-a",
            status="approved",
        )
        self.doc = self.deps.kb_store.update_document_status(
            doc_id=doc.doc_id,
            status="approved",
            reviewed_by="reviewer-1",
            review_notes="approved",
            ragflow_doc_id="rag-retire-1",
        )

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_retire_list_download_and_admin_export(self):
        reviewer_app = _build_app(current_user_id="reviewer-1", deps=self.deps)
        with TestClient(reviewer_app) as client:
            retire_resp = client.post(
                f"/api/knowledge/documents/{self.doc.doc_id}/retire",
                json={
                    "retirement_reason": "Release retired and archived for GMP retention",
                    "retention_until_ms": 4_102_444_800_000,
                },
            )
            self.assertEqual(retire_resp.status_code, 200, retire_resp.text)
            retired = retire_resp.json()
            self.assertEqual(retired["effective_status"], "archived")
            self.assertEqual(retired["retired_by"], "reviewer-1")
            self.assertTrue(Path(retired["archive_manifest_path"]).exists())
            self.assertTrue(Path(retired["archive_package_path"]).exists())

            direct_download = client.get(f"/api/knowledge/documents/{self.doc.doc_id}/download")
            self.assertEqual(direct_download.status_code, 409, direct_download.text)
            self.assertEqual(direct_download.json()["detail"], "document_retired_use_archive_route")

            list_resp = client.get("/api/knowledge/retired-documents")
            self.assertEqual(list_resp.status_code, 200, list_resp.text)
            payload = list_resp.json()
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["items"][0]["doc_id"], self.doc.doc_id)

            retired_download = client.get(f"/api/knowledge/retired-documents/{self.doc.doc_id}/download")
            self.assertEqual(retired_download.status_code, 200, retired_download.text)
            self.assertEqual(retired_download.headers["x-distribution-mode"], "inline_text_watermark")
            self.assertEqual(retired_download.headers["x-watermark-policy-id"], "wm-retired")
            self.assertIn("[受控分发水印]", retired_download.text)

        admin_app = _build_app(current_user_id="admin-1", deps=self.deps)
        with TestClient(admin_app) as client:
            list_resp = client.get("/api/audit/retired-records")
            self.assertEqual(list_resp.status_code, 200, list_resp.text)
            self.assertEqual(list_resp.json()["count"], 1)

            export_resp = client.get(f"/api/audit/retired-records/{self.doc.doc_id}/package")
            self.assertEqual(export_resp.status_code, 200, export_resp.text)
            self.assertEqual(export_resp.headers["content-type"], "application/zip")
            self.assertEqual(
                hashlib.sha256(export_resp.content).hexdigest(),
                export_resp.headers["x-retired-record-package-sha256"],
            )

            archive = ZipFile(io.BytesIO(export_resp.content))
            members = set(archive.namelist())
            self.assertIn("README.txt", members)
            self.assertIn("retirement_manifest.json", members)
            self.assertIn("checksums.json", members)
            self.assertIn("documents/retire_me.txt", members)

        total, audit_rows = self.deps.audit_log_store.list_events(limit=20)
        self.assertGreaterEqual(total, 3)
        actions = [row.action for row in audit_rows]
        self.assertIn("document_retire", actions)
        self.assertIn("retired_document_download", actions)
        self.assertIn("retired_record_package_export", actions)

    def test_unauthorized_user_cannot_access_retired_document(self):
        service = RetiredRecordsService(kb_store=self.deps.kb_store)
        retired = service.retire_document(
            doc_id=self.doc.doc_id,
            retired_by="reviewer-1",
            retired_by_username="reviewer-1",
            retirement_reason="archive test",
            retention_until_ms=4_102_444_800_000,
        )
        self.assertEqual(retired.effective_status, "archived")

        viewer_app = _build_app(current_user_id="viewer-1", deps=self.deps)
        with TestClient(viewer_app) as client:
            resp = client.get(f"/api/knowledge/retired-documents/{self.doc.doc_id}/download")
            self.assertEqual(resp.status_code, 403, resp.text)
            self.assertEqual(resp.json()["detail"], "kb_not_allowed")

    def test_expired_retired_document_returns_gone(self):
        service = RetiredRecordsService(kb_store=self.deps.kb_store)
        retired = service.retire_document(
            doc_id=self.doc.doc_id,
            retired_by="reviewer-1",
            retired_by_username="reviewer-1",
            retirement_reason="expire test",
            retention_until_ms=4_102_444_800_000,
        )
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE kb_documents SET retention_until_ms = ? WHERE doc_id = ?",
                (1, self.doc.doc_id),
            )
            conn.commit()
        finally:
            conn.close()

        reviewer_app = _build_app(current_user_id="reviewer-1", deps=self.deps)
        with TestClient(reviewer_app) as client:
            resp = client.get(f"/api/knowledge/retired-documents/{self.doc.doc_id}/download")
            self.assertEqual(resp.status_code, 410, resp.text)
            self.assertEqual(resp.json()["detail"], "document_retention_expired")

        admin_app = _build_app(current_user_id="admin-1", deps=self.deps)
        with TestClient(admin_app) as client:
            resp = client.get(f"/api/audit/retired-records/{self.doc.doc_id}/package")
            self.assertEqual(resp.status_code, 410, resp.text)
            self.assertEqual(resp.json()["detail"], "document_retention_expired")


if __name__ == "__main__":
    unittest.main()
