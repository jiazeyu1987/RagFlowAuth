import os
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core import authz
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.document_control.router import router as document_control_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.services.document_control import DocumentControlService
from backend.tests.test_document_control_service_unit import _KbStore, _RagflowService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _snapshot(*, kb_ref: str) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=False,
        can_upload=True,
        can_review=True,
        can_download=False,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
        kb_scope=ResourceScope.SET,
        kb_names=frozenset({kb_ref}),
        chat_scope=ResourceScope.NONE,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.NONE,
        tool_ids=frozenset(),
    )


class TestDocumentControlApiUnit(unittest.TestCase):
    def setUp(self):
        self._temp_dir = make_temp_dir(prefix="ragflowauth_doc_control_api")
        self._db_path = os.path.join(str(self._temp_dir), "auth.db")
        ensure_schema(self._db_path)
        self.deps = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=_RagflowService(),
            audit_log_store=AuditLogStore(db_path=self._db_path),
            org_structure_manager=None,
        )

    def tearDown(self):
        cleanup_dir(self._temp_dir)

    def _build_client(self, *, kb_ref: str) -> TestClient:
        app = FastAPI()
        app.include_router(document_control_router, prefix="/api")
        ctx = authz.AuthContext(
            deps=self.deps,
            payload=TokenPayload(sub="reviewer-1"),
            user=SimpleNamespace(
                user_id="reviewer-1",
                username="reviewer",
                role="reviewer",
                status="active",
                company_id=None,
                department_id=None,
            ),
            snapshot=_snapshot(kb_ref=kb_ref),
        )
        app.dependency_overrides[authz.get_auth_context] = lambda: ctx
        return TestClient(app)

    def test_routes_allow_kb_name_variant_and_complete_transition_flow(self):
        with self._build_client(kb_ref="Quality KB") as client:
            create_resp = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-001",
                    "title": "Controlled URS",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.md", b"# urs\n", "text/markdown")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            created = create_resp.json()["document"]
            self.assertEqual(created["target_kb_id"], "kb-quality")
            self.assertEqual(created["target_kb_name"], "Quality KB")
            revision_id = created["current_revision"]["controlled_revision_id"]
            document_id = created["controlled_document_id"]

            list_resp = client.get("/api/quality-system/doc-control/documents?query=Controlled")
            self.assertEqual(list_resp.status_code, 200, list_resp.text)
            self.assertEqual(list_resp.json()["count"], 1)

            detail_resp = client.get(f"/api/quality-system/doc-control/documents/{document_id}")
            self.assertEqual(detail_resp.status_code, 200, detail_resp.text)
            self.assertEqual(detail_resp.json()["document"]["doc_code"], "DOC-API-001")

            for target_status in ("in_review", "approved", "effective"):
                transition_resp = client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/transitions",
                    json={"target_status": target_status, "note": f"move to {target_status}"},
                )
                self.assertEqual(transition_resp.status_code, 200, transition_resp.text)

            final_document = transition_resp.json()["document"]
            self.assertEqual(final_document["effective_revision"]["controlled_revision_id"], revision_id)
            self.assertEqual(final_document["effective_revision"]["status"], "effective")

    def test_create_route_rejects_unmanaged_kb(self):
        with self._build_client(kb_ref="Other KB") as client:
            response = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-002",
                    "title": "Forbidden URS",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                },
                files={"file": ("urs.md", b"# urs\n", "text/markdown")},
            )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"], "kb_not_allowed")


if __name__ == "__main__":
    unittest.main()
