import os
import shutil
import time
import unittest
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core import authz
from backend.app.core.config import settings
from backend.app.core.paths import resolve_repo_path
from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.document_control.router import router as document_control_router
from backend.app.modules.inbox.router import router as inbox_router
from backend.app.modules.knowledge.router import router as knowledge_router
from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.audit_log_store import AuditLogStore
from backend.services.document_control import DocumentControlService
from backend.services.notification import NotificationManager, NotificationStore
from backend.services.training_compliance import TrainingComplianceService
from backend.tests.test_document_control_service_unit import _KbStore, _RagflowService, _UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _snapshot(*, kb_ref: str) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=False,
        can_upload=True,
        can_review=True,
        can_download=True,
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
        can_manage_users=True,
    )


class TestDocumentControlApiUnit(unittest.TestCase):
    def setUp(self):
        self._temp_dir = make_temp_dir(prefix="ragflowauth_doc_control_api")
        self._db_path = os.path.join(str(self._temp_dir), "auth.db")
        self._old_upload_dir = settings.UPLOAD_DIR
        self._managed_upload_dir = os.path.join(
            "data",
            "test_uploads",
            os.path.basename(str(self._temp_dir)).strip() or "ragflowauth_doc_control_api",
        )
        settings.UPLOAD_DIR = self._managed_upload_dir
        self._managed_upload_dir_abs = str(resolve_repo_path(self._managed_upload_dir))
        ensure_schema(self._db_path)
        self.notification_manager = NotificationManager(store=NotificationStore(db_path=self._db_path))
        self.notification_manager.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="站内信",
            enabled=True,
            config={},
        )
        self.training_service = TrainingComplianceService(db_path=self._db_path)
        self.user_store = _UserStore(
            {
                "reviewer-1": SimpleNamespace(user_id="reviewer-1", username="reviewer", status="active"),
                "cosigner-1": SimpleNamespace(user_id="cosigner-1", username="cosigner1", status="active"),
                "cosigner-2": SimpleNamespace(user_id="cosigner-2", username="cosigner2", status="active"),
                "approver-1": SimpleNamespace(user_id="approver-1", username="approver", status="active"),
                "standardizer-1": SimpleNamespace(user_id="standardizer-1", username="standardizer", status="active"),
            }
        )
        self.approval_matrix = {
            "*": [
                {
                    "step_type": "cosign",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 60,
                    "approver_user_ids": ["cosigner-1", "cosigner-2"],
                },
                {
                    "step_type": "approve",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 60,
                    "approver_user_ids": ["approver-1"],
                },
                {
                    "step_type": "standardize_review",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 60,
                    "approver_user_ids": ["standardizer-1"],
                },
            ]
        }
        self.deps = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=_RagflowService(),
            audit_log_store=AuditLogStore(db_path=self._db_path),
            training_compliance_service=self.training_service,
            notification_manager=self.notification_manager,
            org_structure_manager=None,
            user_store=self.user_store,
        )
        service = DocumentControlService.from_deps(self.deps)
        for document_type in ("urs", "sop", "srs", "wi"):
            service.upsert_document_type_workflow(
                document_type=document_type,
                name=f"{document_type} workflow",
                steps=self.approval_matrix["*"],
            )
        requirement_code = "TR-001"
        requirement = self.training_service.get_requirement(requirement_code)
        curriculum_version = str(requirement["curriculum_version"])
        self.training_service.record_training(
            requirement_code=requirement_code,
            user_id="standardizer-1",
            curriculum_version=curriculum_version,
            trainer_user_id="trainer-1",
            training_outcome="passed",
            effectiveness_status="effective",
            effectiveness_score=None,
            effectiveness_summary="ok",
            training_notes=None,
            completed_at_ms=None,
            effectiveness_reviewed_by_user_id="trainer-1",
            effectiveness_reviewed_at_ms=None,
        )
        self.training_service.grant_certification(
            requirement_code=requirement_code,
            user_id="standardizer-1",
            granted_by_user_id="trainer-1",
            certification_status="active",
        )

    def tearDown(self):
        settings.UPLOAD_DIR = self._old_upload_dir
        try:
            shutil.rmtree(self._managed_upload_dir_abs, ignore_errors=True)
        except Exception:
            pass
        cleanup_dir(self._temp_dir)

    def _build_client(
        self,
        *,
        kb_ref: str,
        user_id: str = "reviewer-1",
        username: str = "reviewer",
        role: str = "reviewer",
        department_id: int | None = None,
    ) -> TestClient:
        app = FastAPI()
        app.include_router(document_control_router, prefix="/api")
        app.include_router(knowledge_router, prefix="/api/knowledge")
        app.include_router(inbox_router, prefix="/api")
        ctx = authz.AuthContext(
            deps=self.deps,
            payload=TokenPayload(sub=user_id),
            user=SimpleNamespace(
                user_id=user_id,
                username=username,
                role=role,
                status="active",
                company_id=None,
                department_id=department_id,
            ),
            snapshot=_snapshot(kb_ref=kb_ref),
        )
        app.dependency_overrides[authz.get_auth_context] = lambda: ctx
        return TestClient(app)

    def _seed_active_user(self, *, user_id: str, username: str, department_id: int):
        now_ms = int(time.time() * 1000)
        conn = connect_sqlite(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO users (user_id, username, password_hash, role, department_id, status, created_at_ms)
                VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (str(user_id), str(username), "x", "viewer", int(department_id), now_ms),
            )
            conn.commit()
        finally:
            conn.close()

    def _create_and_approve_to_pending_effective(self, *, kb_ref: str, doc_code: str) -> tuple[str, str]:
        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            create_resp = reviewer_client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": doc_code,
                    "title": "Controlled URS",
                    "document_type": "urs",
                    "target_kb_id": kb_ref,
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            created = create_resp.json()["document"]
            revision_id = created["current_revision"]["controlled_revision_id"]
            document_id = created["controlled_document_id"]

            submit_resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/submit",
                json={"note": "submit"},
            )
            self.assertEqual(submit_resp.status_code, 200, submit_resp.text)

        for user_id, username in (
            ("cosigner-1", "cosigner1"),
            ("cosigner-2", "cosigner2"),
            ("approver-1", "approver"),
            ("standardizer-1", "standardizer"),
        ):
            with self._build_client(kb_ref=kb_ref, user_id=user_id, username=username) as client:
                approve_resp = client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                    json={"note": f"approve by {user_id}"},
                )
                self.assertEqual(approve_resp.status_code, 200, approve_resp.text)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            doc_resp = reviewer_client.get(f"/api/quality-system/doc-control/documents/{document_id}")
            self.assertEqual(doc_resp.status_code, 200, doc_resp.text)
            self.assertEqual(doc_resp.json()["document"]["current_revision"]["status"], "approved_pending_effective")

        self.training_service.upsert_revision_training_gate(
            controlled_revision_id=revision_id,
            training_required=False,
            department_ids=[],
        )
        return document_id, revision_id

    def test_routes_allow_kb_name_variant_and_complete_workflow_flow(self):
        with self._build_client(kb_ref="Quality KB", user_id="reviewer-1", username="reviewer") as reviewer_client:
            create_resp = reviewer_client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-001",
                    "title": "Controlled URS",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            created = create_resp.json()["document"]
            self.assertEqual(created["target_kb_id"], "kb-quality")
            self.assertEqual(created["target_kb_name"], "Quality KB")
            revision_id = created["current_revision"]["controlled_revision_id"]
            kb_doc_id = created["current_revision"]["kb_doc_id"]
            document_id = created["controlled_document_id"]

            self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)
            dept_resp = reviewer_client.put(
                f"/api/quality-system/doc-control/documents/{document_id}/distribution-departments",
                json={"department_ids": [10]},
            )
            self.assertEqual(dept_resp.status_code, 200, dept_resp.text)

            list_resp = reviewer_client.get("/api/quality-system/doc-control/documents?query=Controlled")
            self.assertEqual(list_resp.status_code, 200, list_resp.text)
            self.assertEqual(list_resp.json()["count"], 1)

            detail_resp = reviewer_client.get(f"/api/quality-system/doc-control/documents/{document_id}")
            self.assertEqual(detail_resp.status_code, 200, detail_resp.text)
            self.assertEqual(detail_resp.json()["document"]["doc_code"], "DOC-API-001")

            submit_resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/submit",
                json={"note": "submit for approval"},
            )
            self.assertEqual(submit_resp.status_code, 200, submit_resp.text)
            self.assertEqual(submit_resp.json()["document"]["current_revision"]["status"], "approval_in_progress")

            with self._build_client(kb_ref="Quality KB", user_id="cosigner-1", username="cosigner1") as cosigner1_client:
                approve_resp = cosigner1_client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                    json={"note": "cosign 1"},
                )
                self.assertEqual(approve_resp.status_code, 200, approve_resp.text)

            with self._build_client(kb_ref="Quality KB", user_id="cosigner-2", username="cosigner2") as cosigner2_client:
                approve_resp = cosigner2_client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                    json={"note": "cosign 2"},
                )
                self.assertEqual(approve_resp.status_code, 200, approve_resp.text)
                self.assertEqual(approve_resp.json()["document"]["current_revision"]["current_approval_step_name"], "approve")

            with self._build_client(kb_ref="Quality KB", user_id="approver-1", username="approver") as approver_client:
                approve_resp = approver_client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                    json={"note": "approve"},
                )
                self.assertEqual(approve_resp.status_code, 200, approve_resp.text)
                self.assertEqual(
                    approve_resp.json()["document"]["current_revision"]["current_approval_step_name"],
                    "standardize_review",
                )

            with self._build_client(
                kb_ref="Quality KB", user_id="standardizer-1", username="standardizer"
            ) as standardizer_client:
                final_resp = standardizer_client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                    json={"note": "standardize ok"},
                )
                self.assertEqual(final_resp.status_code, 200, final_resp.text)
                self.training_service.upsert_revision_training_gate(
                    controlled_revision_id=revision_id,
                    training_required=False,
                    department_ids=[],
                )
                publish_resp = standardizer_client.post(
                    f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                    json={"release_mode": "manual_by_doc_control", "note": "publish"},
                )
                self.assertEqual(publish_resp.status_code, 200, publish_resp.text)
                self.assertEqual(publish_resp.json()["document"]["effective_revision"]["status"], "effective")

            final_document = final_resp.json()["document"]
            self.assertEqual(final_document["current_revision"]["controlled_revision_id"], revision_id)
            self.assertEqual(final_document["current_revision"]["status"], "approved_pending_effective")
            self.assertIsNone(final_document["current_revision"]["approval_request_id"])

            initiate_resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/obsolete/initiate",
                json={
                    "retirement_reason": "obsolete for controlled retention",
                    "retention_until_ms": 4_102_444_800_000,
                    "note": "initiate obsolete",
                },
            )
            self.assertEqual(initiate_resp.status_code, 200, initiate_resp.text)

        with self._build_client(kb_ref="Quality KB", user_id="approver-1", username="approver") as approver_client:
            approve_obsolete = approver_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/obsolete/approve",
                json={"note": "approve obsolete"},
            )
            self.assertEqual(approve_obsolete.status_code, 200, approve_obsolete.text)
            self.assertIsNone(approve_obsolete.json()["document"]["effective_revision"])

            kb_doc = self.deps.kb_store.get_document(kb_doc_id)
            self.assertEqual(getattr(kb_doc, "effective_status", None), "archived")
            self.assertEqual(getattr(kb_doc, "retention_until_ms", None), 4_102_444_800_000)

            direct_download = approver_client.get(f"/api/knowledge/documents/{kb_doc_id}/download")
            self.assertEqual(direct_download.status_code, 409, direct_download.text)
            self.assertEqual(direct_download.json()["detail"], "document_retired_use_archive_route")

    def test_transitions_endpoint_removed(self):
        with self._build_client(kb_ref="Quality KB", user_id="reviewer-1", username="reviewer") as reviewer_client:
            create_resp = reviewer_client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-TRANS-001",
                    "title": "Removed transitions",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            revision_id = create_resp.json()["document"]["current_revision"]["controlled_revision_id"]

            resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/transitions",
                json={"target_status": "in_review", "note": "move to in_review"},
            )
            self.assertEqual(resp.status_code, 404, resp.text)

    def test_create_route_rejects_unmanaged_kb(self):
        with self._build_client(kb_ref="Other KB") as client:
            response = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-002",
                    "title": "Forbidden URS",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"], "kb_not_allowed")

    def test_create_route_requires_product_and_registration_metadata(self):
        with self._build_client(kb_ref="Quality KB") as client:
            response = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-003",
                    "title": "Missing metadata",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"], "product_name_required")

    def test_create_route_rejects_non_pdf_upload(self):
        with self._build_client(kb_ref="Quality KB") as client:
            response = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-003B",
                    "title": "Non PDF",
                    "document_type": "urs",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.md", b"# urs\n", "text/markdown")},
            )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"], "document_control_pdf_required")

    def test_same_reviewer_cannot_approve_revision(self):
        with self._build_client(kb_ref="Quality KB", user_id="reviewer-1", username="reviewer") as client:
            create_resp = client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-004",
                    "title": "Approval separation",
                    "document_type": "sop",
                    "target_kb_id": "Quality KB",
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("sop.pdf", b"%PDF-1.4 sop\n", "application/pdf")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            revision_id = create_resp.json()["document"]["current_revision"]["controlled_revision_id"]

            submit_resp = client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/submit",
                json={"note": "submit"},
            )
            self.assertEqual(submit_resp.status_code, 200, submit_resp.text)

            approval_resp = client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/approve",
                json={"note": "same reviewer approval"},
            )

        self.assertEqual(approval_resp.status_code, 409, approval_resp.text)
        self.assertEqual(approval_resp.json()["detail"], "document_control_approval_role_conflict")

    def test_publish_fails_fast_when_distribution_departments_missing(self):
        kb_ref = "Quality KB"
        _, revision_id = self._create_and_approve_to_pending_effective(kb_ref=kb_ref, doc_code="DOC-API-WS04-001")
        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            publish_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                json={"release_mode": "manual_by_doc_control", "note": "publish"},
            )
            self.assertEqual(publish_resp.status_code, 409, publish_resp.text)
            self.assertEqual(publish_resp.json()["detail"], "document_control_distribution_departments_missing")

    def test_publish_creates_department_acks_and_inbox_notifications(self):
        kb_ref = "Quality KB"
        document_id, revision_id = self._create_and_approve_to_pending_effective(kb_ref=kb_ref, doc_code="DOC-API-WS04-002")

        self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)
        self._seed_active_user(user_id="dept20-user-1", username="dept20-user-1", department_id=20)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            set_resp = reviewer_client.put(
                f"/api/quality-system/doc-control/documents/{document_id}/distribution-departments",
                json={"department_ids": [10, 20]},
            )
            self.assertEqual(set_resp.status_code, 200, set_resp.text)

        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            publish_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                json={"release_mode": "automatic", "note": "publish"},
            )
            self.assertEqual(publish_resp.status_code, 200, publish_resp.text)
        self.notification_manager.dispatch_pending(limit=200)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            acks_resp = reviewer_client.get(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks",
            )
            self.assertEqual(acks_resp.status_code, 200, acks_resp.text)
            self.assertEqual(acks_resp.json()["count"], 2)
            statuses = {item["department_id"]: item["status"] for item in acks_resp.json()["items"]}
            self.assertEqual(statuses[10], "pending")
            self.assertEqual(statuses[20], "pending")

        with self._build_client(
            kb_ref=kb_ref,
            user_id="dept10-user-1",
            username="dept10-user-1",
            role="viewer",
            department_id=10,
        ) as dept10_client:
            inbox_resp = dept10_client.get("/api/inbox")
            self.assertEqual(inbox_resp.status_code, 200, inbox_resp.text)
            self.assertTrue(
                any(item.get("event_type") == "document_control_department_ack_required" for item in inbox_resp.json()["items"])
            )

    def test_manual_release_requires_archive_completion_before_department_acks_exist(self):
        kb_ref = "Quality KB"
        document_id, revision_id = self._create_and_approve_to_pending_effective(kb_ref=kb_ref, doc_code="DOC-API-WS03-MANUAL")
        self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            set_resp = reviewer_client.put(
                f"/api/quality-system/doc-control/documents/{document_id}/distribution-departments",
                json={"department_ids": [10]},
            )
            self.assertEqual(set_resp.status_code, 200, set_resp.text)

        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            publish_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                json={"release_mode": "manual_by_doc_control", "note": "publish manual"},
            )
            self.assertEqual(publish_resp.status_code, 200, publish_resp.text)

            acks_before = standardizer_client.get(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks",
            )
            self.assertEqual(acks_before.status_code, 200, acks_before.text)
            self.assertEqual(acks_before.json()["count"], 0)

            complete_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish/manual-archive-complete",
                json={"note": "manual archive done"},
            )
            self.assertEqual(complete_resp.status_code, 200, complete_resp.text)

            acks_after = standardizer_client.get(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks",
            )
            self.assertEqual(acks_after.status_code, 200, acks_after.text)
            self.assertEqual(acks_after.json()["count"], 1)

        with self._build_client(
            kb_ref=kb_ref,
            user_id="dept10-user-1",
            username="dept10-user-1",
            role="viewer",
            department_id=10,
        ) as dept10_client:
            inbox_resp = dept10_client.get("/api/inbox")
            self.assertEqual(inbox_resp.status_code, 200, inbox_resp.text)
            self.assertTrue(
                any(item.get("event_type") == "document_control_department_ack_required" for item in inbox_resp.json()["items"])
            )

    def test_department_ack_confirm_enforces_department_ownership_and_is_idempotent(self):
        kb_ref = "Quality KB"
        document_id, revision_id = self._create_and_approve_to_pending_effective(kb_ref=kb_ref, doc_code="DOC-API-WS04-003")
        self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)
        self._seed_active_user(user_id="dept20-user-1", username="dept20-user-1", department_id=20)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            set_resp = reviewer_client.put(
                f"/api/quality-system/doc-control/documents/{document_id}/distribution-departments",
                json={"department_ids": [10, 20]},
            )
            self.assertEqual(set_resp.status_code, 200, set_resp.text)

        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            publish_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                json={"release_mode": "automatic", "note": "publish"},
            )
            self.assertEqual(publish_resp.status_code, 200, publish_resp.text)

        with self._build_client(
            kb_ref=kb_ref,
            user_id="dept10-user-1",
            username="dept10-user-1",
            role="viewer",
            department_id=10,
        ) as dept10_client:
            confirm_resp = dept10_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks/10/confirm",
                json={"notes": "ok"},
            )
            self.assertEqual(confirm_resp.status_code, 200, confirm_resp.text)
            ack = confirm_resp.json()["ack"]
            self.assertEqual(ack["status"], "confirmed")
            self.assertEqual(ack["confirmed_by_user_id"], "dept10-user-1")

            confirm_resp_2 = dept10_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks/10/confirm",
                json={"notes": "still ok"},
            )
            self.assertEqual(confirm_resp_2.status_code, 200, confirm_resp_2.text)
            self.assertEqual(confirm_resp_2.json()["ack"]["status"], "confirmed")
            self.assertEqual(confirm_resp_2.json()["ack"]["notes"], "still ok")

        with self._build_client(
            kb_ref=kb_ref,
            user_id="dept20-user-1",
            username="dept20-user-1",
            role="viewer",
            department_id=20,
        ) as dept20_client:
            forbidden_resp = dept20_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks/10/confirm",
                json={"notes": "wrong dept"},
            )
            self.assertEqual(forbidden_resp.status_code, 403, forbidden_resp.text)
            self.assertEqual(forbidden_resp.json()["detail"], "document_control_department_ack_forbidden")

    def test_remind_overdue_marks_overdue_and_sends_inbox(self):
        kb_ref = "Quality KB"
        document_id, revision_id = self._create_and_approve_to_pending_effective(kb_ref=kb_ref, doc_code="DOC-API-WS04-004")
        self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)
        self._seed_active_user(user_id="dept20-user-1", username="dept20-user-1", department_id=20)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            set_resp = reviewer_client.put(
                f"/api/quality-system/doc-control/documents/{document_id}/distribution-departments",
                json={"department_ids": [10, 20]},
            )
            self.assertEqual(set_resp.status_code, 200, set_resp.text)

        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            publish_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/publish",
                json={"release_mode": "automatic", "note": "publish"},
            )
            self.assertEqual(publish_resp.status_code, 200, publish_resp.text)

        past_ms = int(time.time() * 1000) - 1000
        conn = connect_sqlite(self._db_path)
        try:
            conn.execute(
                """
                UPDATE document_control_department_acks
                SET due_at_ms = ?
                WHERE controlled_revision_id = ?
                """,
                (past_ms, revision_id),
            )
            conn.commit()
        finally:
            conn.close()

        with self._build_client(kb_ref=kb_ref, user_id="standardizer-1", username="standardizer") as standardizer_client:
            remind_resp = standardizer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks/remind-overdue",
                json={"note": "remind"},
            )
            self.assertEqual(remind_resp.status_code, 200, remind_resp.text)
            self.assertEqual(remind_resp.json()["result"]["count"], 2)
        self.notification_manager.dispatch_pending(limit=200)

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            acks_resp = reviewer_client.get(
                f"/api/quality-system/doc-control/revisions/{revision_id}/department-acks",
            )
            self.assertEqual(acks_resp.status_code, 200, acks_resp.text)
            statuses = {item["department_id"]: item["status"] for item in acks_resp.json()["items"]}
            self.assertEqual(statuses[10], "overdue")
            self.assertEqual(statuses[20], "overdue")

        with self._build_client(
            kb_ref=kb_ref,
            user_id="dept10-user-1",
            username="dept10-user-1",
            role="viewer",
            department_id=10,
        ) as dept10_client:
            inbox_resp = dept10_client.get("/api/inbox")
            self.assertEqual(inbox_resp.status_code, 200, inbox_resp.text)
            self.assertTrue(
                any(item.get("event_type") == "document_control_department_ack_overdue" for item in inbox_resp.json()["items"])
            )

    def test_remind_overdue_approval_step_endpoint(self):
        kb_ref = "Quality KB"
        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            create_resp = reviewer_client.post(
                "/api/quality-system/doc-control/documents",
                data={
                    "doc_code": "DOC-API-WS01-REMIND",
                    "title": "Approval overdue",
                    "document_type": "urs",
                    "target_kb_id": kb_ref,
                    "product_name": "Product A",
                    "registration_ref": "REG-001",
                },
                files={"file": ("urs.pdf", b"%PDF-1.4 urs\n", "application/pdf")},
            )
            self.assertEqual(create_resp.status_code, 200, create_resp.text)
            revision_id = create_resp.json()["document"]["current_revision"]["controlled_revision_id"]
            submit_resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/submit",
                json={"note": "submit"},
            )
            self.assertEqual(submit_resp.status_code, 200, submit_resp.text)

        conn = connect_sqlite(self._db_path)
        try:
            past_ms = int(time.time() * 1000) - 61 * 60 * 1000
            conn.execute(
                """
                UPDATE operation_approval_request_steps
                SET activated_at_ms = ?
                WHERE request_id = (
                    SELECT approval_request_id
                    FROM controlled_revisions
                    WHERE controlled_revision_id = ?
                )
                  AND step_no = 1
                """,
                (past_ms, revision_id),
            )
            conn.commit()
        finally:
            conn.close()

        with self._build_client(kb_ref=kb_ref, user_id="reviewer-1", username="reviewer") as reviewer_client:
            remind_resp = reviewer_client.post(
                f"/api/quality-system/doc-control/revisions/{revision_id}/approval/remind-overdue",
                json={"note": "remind overdue approval"},
            )
            self.assertEqual(remind_resp.status_code, 200, remind_resp.text)
            self.assertEqual(remind_resp.json()["result"]["count"], 2)


if __name__ == "__main__":
    unittest.main()
