import hashlib
import io
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from authx import TokenPayload
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.app.core import auth as auth_module
from backend.app.modules.audit.router import router as audit_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_compliance_repo(root: Path) -> None:
    docs = {
        "docs/compliance/urs.md": "# URS\n\n版本: v1.0\n更新时间: 2026-04-03\n\nURS-012 FDA-03\n",
        "docs/compliance/srs.md": "# SRS\n\n版本: v1.0\n更新时间: 2026-04-03\n\nSRS-012 URS-012\n",
        "docs/compliance/traceability_matrix.md": "# Matrix\n\n版本: v1.0\n更新时间: 2026-04-03\n\nFDA-03 SRS-012 test_fda03_compliance_gate_unit\n",
        "docs/compliance/validation_plan.md": (
            "# Plan\n\n版本: v1.0\n更新时间: 2026-04-03\n\n"
            "validate_fda03_repo_compliance.py\n"
            "test_compliance_review_package_api_unit\n"
        ),
        "docs/compliance/validation_report.md": (
            "# Report\n\n版本: v1.0\n更新时间: 2026-04-03\n\nFDA-03\nvalidate_fda03_repo_compliance.py\n"
        ),
        "docs/compliance/release_and_retirement_sop.md": "# SOP\n\n版本: v1.0\n更新时间: 2026-04-03\n",
        "docs/compliance/approval_workflow_sop.md": "# SOP\n\n版本: v1.1\n更新时间: 2026-04-03\n",
        "docs/compliance/electronic_signature_policy.md": "# Policy\n\n版本: v1.1\n更新时间: 2026-04-03\n",
        "docs/compliance/backup_restore_sop.md": "# Backup SOP\n\n版本: v1.1\n更新时间: 2026-04-03\n",
        "docs/compliance/review_package_sop.md": (
            "# Review Package SOP\n\n版本: v1.0\n更新时间: 2026-04-03\n"
            "/api/audit/controlled-documents\n/api/audit/review-package\nreview_package_manifest.json\n"
            "线下签字版批准页\n"
        ),
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)
    _write(
        root / "docs/compliance/controlled_document_register.md",
        """# Register

版本: v1.0
更新时间: 2026-04-03
当前发布版本: 2.0.0

| doc_code | title | file_path | version | status | effective_date | review_due_date | approved_release_version | package_group |
|---|---|---|---|---|---|---|---|---|
| CD-001 | URS | docs/compliance/urs.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | requirements |
| CD-002 | SRS | docs/compliance/srs.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | requirements |
| CD-003 | Traceability | docs/compliance/traceability_matrix.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | validation |
| CD-004 | Validation Plan | docs/compliance/validation_plan.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | validation |
| CD-005 | Release SOP | docs/compliance/release_and_retirement_sop.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | sop |
| CD-006 | Review Package SOP | docs/compliance/review_package_sop.md | v1.0 | effective | 2026-04-03 | 2026-10-03 | 2.0.0 | package |
""",
    )


class _User:
    def __init__(self, role: str):
        self.user_id = "u1"
        self.username = "admin1" if role == "admin" else "viewer1"
        self.email = f"{self.username}@example.com"
        self.role = role
        self.status = "active"
        self.group_id = None
        self.group_ids = []
        self.company_id = 1
        self.department_id = 2


class _UserStore:
    def __init__(self, user: _User):
        self._user = user

    def get_by_user_id(self, user_id: str):  # noqa: ARG002
        return self._user


class _PermissionGroupStore:
    def get_group(self, group_id: int):  # noqa: ARG002
        return None


class _UserKbPermissionStore:
    def get_user_kbs(self, user_id: str):  # noqa: ARG002
        return []


class _UserChatPermissionStore:
    def get_user_chats(self, user_id: str):  # noqa: ARG002
        return []


class _Deps:
    def __init__(self, *, db_path: str, role: str):
        audit_store = AuditLogStore(db_path=db_path)
        self.user_store = _UserStore(_User(role=role))
        self.permission_group_store = _PermissionGroupStore()
        self.user_kb_permission_store = _UserKbPermissionStore()
        self.user_chat_permission_store = _UserChatPermissionStore()
        self.user_tool_permission_store = SimpleNamespace(list_tool_ids=lambda *_args, **_kwargs: [])
        self.audit_log_store = audit_store
        self.audit_log_manager = AuditLogManager(store=audit_store)


def _override_get_current_payload(_: Request) -> TokenPayload:
    return TokenPayload(sub="u1")


class TestComplianceReviewPackageApiUnit(unittest.TestCase):
    def test_admin_can_list_and_export_review_package(self):
        td = make_temp_dir(prefix="ragflowauth_fda03_package")
        try:
            repo_root = Path(td) / "repo"
            _build_compliance_repo(repo_root)
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            app.state.deps = _Deps(db_path=db_path, role="admin")
            app.state.compliance_repo_root = str(repo_root)
            app.include_router(audit_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                list_resp = client.get("/api/audit/controlled-documents")
                export_resp = client.get("/api/audit/review-package?company_id=9")

            self.assertEqual(list_resp.status_code, 200, list_resp.text)
            list_body = list_resp.json()
            self.assertEqual(list_body["release_version"], "2.0.0")
            self.assertEqual(list_body["count"], 6)
            self.assertTrue(all(item["release_matches"] for item in list_body["items"]))

            self.assertEqual(export_resp.status_code, 200, export_resp.text)
            self.assertEqual(export_resp.headers["content-type"], "application/zip")
            self.assertIn("review_package_2.0.0_", export_resp.headers["content-disposition"])
            self.assertEqual(
                hashlib.sha256(export_resp.content).hexdigest(),
                export_resp.headers["x-review-package-sha256"],
            )

            archive = ZipFile(io.BytesIO(export_resp.content))
            members = set(archive.namelist())
            self.assertIn("review_package_manifest.json", members)
            self.assertIn("review_package_checksums.json", members)
            self.assertIn("controlled_documents.json", members)
            self.assertIn("controlled_documents.csv", members)
            self.assertIn("documents/urs.md", members)
            self.assertIn("documents/review_package_sop.md", members)

            manifest = json.loads(archive.read("review_package_manifest.json").decode("utf-8"))
            checksums = json.loads(archive.read("review_package_checksums.json").decode("utf-8"))
            self.assertEqual(manifest["files"], checksums)
            self.assertEqual(manifest["metadata"]["release_version"], "2.0.0")
            self.assertEqual(manifest["metadata"]["company_id"], 9)
            self.assertEqual(manifest["metadata"]["tenant_key"], "company_9")
            self.assertEqual(manifest["metadata"]["register_path"], "docs/compliance/controlled_document_register.md")
            self.assertEqual(
                {item["package_group"] for item in manifest["documents"]},
                {"requirements", "validation", "sop", "package"},
            )
            self.assertEqual(
                hashlib.sha256(archive.read("controlled_documents.csv")).hexdigest(),
                manifest["files"]["controlled_documents.csv"]["sha256"],
            )

            exported_events = app.state.deps.audit_log_store.list_events(
                action="compliance_review_package_export",
                limit=10,
            )[1]
            self.assertEqual(len(exported_events), 1)
            self.assertEqual(exported_events[0].resource_type, "controlled_document_review_package")
        finally:
            cleanup_dir(td)

    def test_non_admin_cannot_export_review_package(self):
        td = make_temp_dir(prefix="ragflowauth_fda03_package_deny")
        try:
            repo_root = Path(td) / "repo"
            _build_compliance_repo(repo_root)
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            app = FastAPI()
            app.state.deps = _Deps(db_path=db_path, role="viewer")
            app.state.compliance_repo_root = str(repo_root)
            app.include_router(audit_router, prefix="/api")
            app.dependency_overrides[auth_module.get_current_payload] = _override_get_current_payload

            with TestClient(app) as client:
                resp = client.get("/api/audit/review-package")

            self.assertEqual(resp.status_code, 403, resp.text)
            self.assertEqual(resp.json()["detail"], "audit_events_forbidden")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
