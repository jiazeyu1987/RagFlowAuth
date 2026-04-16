import io
import json
import os
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.app.core.config import settings
from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.audit_log_store import AuditLogStore
from backend.services.document_control import DocumentControlError, DocumentControlService
from backend.services.notification import NotificationManager, NotificationStore
from backend.services.training_compliance import TrainingComplianceService
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str = "application/pdf"):
        self.filename = filename
        self.content_type = content_type
        self.file = io.BytesIO(content)


class _KbStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_document(self, **kwargs):
        now_ms = int(time.time() * 1000)
        doc_id = f"kb-{now_ms}-{kwargs['version_no']}"
        conn = connect_sqlite(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO kb_documents (
                    doc_id,
                    filename,
                    file_path,
                    file_size,
                    mime_type,
                    uploaded_by,
                    status,
                    uploaded_at_ms,
                    reviewed_by,
                    reviewed_at_ms,
                    review_notes,
                    ragflow_doc_id,
                    kb_id,
                    kb_dataset_id,
                    kb_name,
                    logical_doc_id,
                    version_no,
                    previous_doc_id,
                    superseded_by_doc_id,
                    is_current,
                    effective_status,
                    archived_at_ms,
                    retention_until_ms,
                    file_sha256,
                    retired_by,
                    retirement_reason,
                    archive_manifest_path,
                    archive_package_path,
                    archive_package_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
                """,
                (
                    doc_id,
                    kwargs["filename"],
                    kwargs["file_path"],
                    kwargs["file_size"],
                    kwargs["mime_type"],
                    kwargs["uploaded_by"],
                    kwargs.get("status", "draft"),
                    now_ms,
                    kwargs["kb_id"],
                    kwargs.get("kb_dataset_id"),
                    kwargs.get("kb_name"),
                    kwargs.get("logical_doc_id", kwargs.get("controlled_document_id") or doc_id),
                    int(kwargs.get("version_no", 1)),
                    kwargs.get("previous_doc_id"),
                    1 if kwargs.get("is_current", True) else 0,
                    kwargs.get("effective_status"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(doc_id)

    def get_document(self, doc_id: str):
        conn = connect_sqlite(self.db_path)
        try:
            row = conn.execute("SELECT * FROM kb_documents WHERE doc_id = ?", (doc_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return SimpleNamespace(**dict(row))

    def update_document_status(
        self,
        *,
        doc_id: str,
        status: str,
        reviewed_by: str | None = None,
        review_notes: str | None = None,
        ragflow_doc_id: str | None = None,
    ):
        now_ms = int(time.time() * 1000)
        conn = connect_sqlite(self.db_path)
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET status = ?,
                    reviewed_by = ?,
                    reviewed_at_ms = ?,
                    review_notes = ?,
                    ragflow_doc_id = ?,
                    effective_status = ?
                WHERE doc_id = ?
                """,
                (status, reviewed_by, now_ms, review_notes, ragflow_doc_id, status, doc_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_document(doc_id)

    def retire_document(
        self,
        *,
        doc_id: str,
        archived_file_path: str,
        archive_manifest_path: str,
        archive_package_path: str,
        archive_package_sha256: str,
        retired_by: str,
        retirement_reason: str,
        retention_until_ms: int,
        archived_at_ms: int | None = None,
        conn=None,
    ):
        archived_at_ms = int(time.time() * 1000) if archived_at_ms is None else int(archived_at_ms)
        retention_until_ms = int(retention_until_ms)
        retired_by = str(retired_by or "").strip()
        retirement_reason = str(retirement_reason or "").strip()

        owns_conn = False
        if conn is None:
            conn = connect_sqlite(self.db_path)
            owns_conn = True
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET file_path = ?,
                    is_current = 0,
                    effective_status = 'archived',
                    archived_at_ms = ?,
                    retention_until_ms = ?,
                    retired_by = ?,
                    retirement_reason = ?,
                    archive_manifest_path = ?,
                    archive_package_path = ?,
                    archive_package_sha256 = ?
                WHERE doc_id = ?
                """,
                (
                    str(archived_file_path),
                    archived_at_ms,
                    retention_until_ms,
                    retired_by,
                    retirement_reason,
                    str(archive_manifest_path),
                    str(archive_package_path),
                    str(archive_package_sha256),
                    str(doc_id),
                ),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()
        return self.get_document(str(doc_id))

    def delete_document(self, doc_id: str):
        conn = connect_sqlite(self.db_path)
        try:
            conn.execute("DELETE FROM kb_documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    def retire_document(
        self,
        *,
        doc_id: str,
        archived_file_path: str,
        archive_manifest_path: str,
        archive_package_path: str,
        archive_package_sha256: str,
        retired_by: str,
        retirement_reason: str,
        retention_until_ms: int,
        archived_at_ms: int | None = None,
        conn=None,
    ):
        archived_at_ms = int(time.time() * 1000) if archived_at_ms is None else int(archived_at_ms)
        owns_conn = False
        if conn is None:
            conn = connect_sqlite(self.db_path)
            owns_conn = True
        try:
            conn.execute(
                """
                UPDATE kb_documents
                SET file_path = ?,
                    is_current = 0,
                    effective_status = 'archived',
                    archived_at_ms = ?,
                    retention_until_ms = ?,
                    retired_by = ?,
                    retirement_reason = ?,
                    archive_manifest_path = ?,
                    archive_package_path = ?,
                    archive_package_sha256 = ?
                WHERE doc_id = ?
                """,
                (
                    str(archived_file_path),
                    archived_at_ms,
                    int(retention_until_ms),
                    str(retired_by),
                    str(retirement_reason),
                    str(archive_manifest_path),
                    str(archive_package_path),
                    str(archive_package_sha256),
                    str(doc_id),
                ),
            )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()
        return self.get_document(str(doc_id))


class _RagflowService:
    def __init__(self):
        self.deleted = []

    def normalize_dataset_id(self, kb_ref: str):
        if kb_ref in {"Quality KB", "kb-quality"}:
            return "kb-quality"
        return None

    def resolve_dataset_name(self, kb_ref: str):
        if kb_ref in {"Quality KB", "kb-quality"}:
            return "Quality KB"
        return kb_ref

    def upload_document_blob(self, **kwargs):  # noqa: ARG002
        return "rag-doc-1"

    def parse_document(self, **kwargs):  # noqa: ARG002
        return True

    def delete_document(self, document_id: str, dataset_name: str = ""):
        self.deleted.append({"document_id": document_id, "dataset_name": dataset_name})
        return True


class _UserStore:
    def __init__(self, users: dict[str, object]):
        self._users = dict(users)

    def get_by_user_id(self, user_id: str):
        return self._users.get(str(user_id))


class TestDocumentControlServiceUnit(unittest.TestCase):
    def setUp(self):
        self._temp_dir = make_temp_dir(prefix="ragflowauth_doc_control_service")
        self._db_path = os.path.join(str(self._temp_dir), "auth.db")
        self._old_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = str(Path(self._temp_dir) / "uploads")
        ensure_schema(self._db_path)
        self.audit_log_store = AuditLogStore(db_path=self._db_path)
        self.ragflow_service = _RagflowService()
        self.notification_manager = NotificationManager(store=NotificationStore(db_path=self._db_path))
        self.notification_manager.upsert_channel(
            channel_id="inapp-main",
            channel_type="in_app",
            name="站内信",
            enabled=True,
            config={},
        )
        self._matrix_path = os.path.join(str(self._temp_dir), "document_control_matrix.json")
        with open(self._matrix_path, "w", encoding="utf-8") as handle:
            json.dump(
                [
                    {
                        "文件小类": "urs",
                        "编制": "项目负责人",
                        "审核会签": {"QA": "●", "QMS": "", "文档管理员": "●"},
                        "批准": "编制部门负责人或授权代表",
                    },
                    {
                        "文件小类": "sop",
                        "编制": "项目负责人",
                        "审核会签": {"QA": "●", "QMS": "", "文档管理员": "●"},
                        "批准": "编制部门负责人或授权代表",
                    },
                    {
                        "文件小类": "srs",
                        "编制": "项目负责人",
                        "审核会签": {"QA": "●", "QMS": "", "文档管理员": "●"},
                        "批准": "编制部门负责人或授权代表",
                    },
                    {
                        "文件小类": "wi",
                        "编制": "项目负责人",
                        "审核会签": {"QA": "●", "QMS": "", "文档管理员": "●"},
                        "批准": "编制部门负责人或授权代表",
                    },
                ],
                handle,
                ensure_ascii=False,
                indent=2,
            )
        self.user_store = _UserStore(
            {
                "reviewer-1": SimpleNamespace(user_id="reviewer-1", username="reviewer", status="active", full_name="Reviewer One"),
                "cosigner-1": SimpleNamespace(user_id="cosigner-1", username="cosigner1", status="active", full_name="Cosigner One"),
                "cosigner-2": SimpleNamespace(user_id="cosigner-2", username="cosigner2", status="active", full_name="Cosigner Two"),
                "cosigner-3": SimpleNamespace(user_id="cosigner-3", username="cosigner3", status="active", full_name="Cosigner Three"),
                "approver-1": SimpleNamespace(user_id="approver-1", username="approver", status="active", full_name="Approver One"),
                "standardizer-1": SimpleNamespace(user_id="standardizer-1", username="standardizer", status="active", full_name="Standardizer One"),
                "docctrl-1": SimpleNamespace(user_id="docctrl-1", username="docctrl", status="active", full_name="Doc Control One"),
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
        self.training_service = TrainingComplianceService(db_path=self._db_path)
        self.deps = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=self.ragflow_service,
            audit_log_store=self.audit_log_store,
            training_compliance_service=self.training_service,
            notification_manager=self.notification_manager,
            org_structure_manager=None,
            user_store=self.user_store,
            document_control_matrix_json_path=self._matrix_path,
            quality_system_config_service=SimpleNamespace(
                get_config=lambda: {
                    "positions": [
                        {"name": "项目负责人", "assigned_users": [{"user_id": "reviewer-1", "username": "reviewer", "full_name": "Reviewer One"}]},
                        {
                            "name": "QA",
                            "assigned_users": [
                                {"user_id": "cosigner-1", "username": "cosigner1", "full_name": "Cosigner One"},
                                {"user_id": "cosigner-2", "username": "cosigner2", "full_name": "Cosigner Two"},
                            ],
                        },
                        {"name": "文档管理员", "assigned_users": [{"user_id": "standardizer-1", "username": "standardizer", "full_name": "Standardizer One"}]},
                        {"name": "编制部门负责人或授权代表", "assigned_users": [{"user_id": "approver-1", "username": "approver", "full_name": "Approver One"}]},
                    ]
                }
            ),
        )
        self.service = DocumentControlService.from_deps(self.deps)
        for document_type in ("urs", "sop", "srs", "wi"):
            self.service.upsert_document_type_workflow(
                document_type=document_type,
                name=f"{document_type} workflow",
                steps=self.approval_matrix["*"],
            )
        self.submitter_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="reviewer-1"),
            user=SimpleNamespace(
                user_id="reviewer-1",
                username="reviewer",
                company_id=None,
                department_id=None,
            ),
        )
        self.cosigner1_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="cosigner-1"),
            user=SimpleNamespace(
                user_id="cosigner-1",
                username="cosigner1",
                company_id=None,
                department_id=None,
            ),
        )
        self.cosigner2_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="cosigner-2"),
            user=SimpleNamespace(
                user_id="cosigner-2",
                username="cosigner2",
                company_id=None,
                department_id=None,
            ),
        )
        self.cosigner3_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="cosigner-3"),
            user=SimpleNamespace(
                user_id="cosigner-3",
                username="cosigner3",
                company_id=None,
                department_id=None,
            ),
        )
        self.approver_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="approver-1"),
            user=SimpleNamespace(
                user_id="approver-1",
                username="approver",
                company_id=None,
                department_id=None,
            ),
        )
        self.standardizer_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="standardizer-1"),
            user=SimpleNamespace(
                user_id="standardizer-1",
                username="standardizer",
                company_id=None,
                department_id=None,
            ),
        )
        self.publisher_ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="docctrl-1"),
            user=SimpleNamespace(
                user_id="docctrl-1",
                username="docctrl",
                role="doc_control",
                company_id=None,
                department_id=None,
            ),
        )

    def tearDown(self):
        settings.UPLOAD_DIR = self._old_upload_dir
        cleanup_dir(self._temp_dir)

    def _seed_doc_review_training_gate(self, *, user_id: str, role_code: str) -> str:  # noqa: ARG002
        requirement_code = "TR-001"
        requirement = self.training_service.get_requirement(requirement_code)
        curriculum_version = str(requirement["curriculum_version"])
        self.training_service.record_training(
            requirement_code=requirement_code,
            user_id=user_id,
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
            user_id=user_id,
            granted_by_user_id="trainer-1",
            certification_status="active",
        )
        return requirement_code

    def _configure_revision_training_gate(self, *, controlled_revision_id: str, training_required: bool, department_ids: list[int] | None = None):
        return self.training_service.upsert_revision_training_gate(
            controlled_revision_id=controlled_revision_id,
            training_required=training_required,
            department_ids=department_ids or [],
        )

    def _approve_revision_to_pending_effective(self, *, controlled_revision_id: str) -> None:
        self.service.submit_revision_for_approval(
            controlled_revision_id=controlled_revision_id,
            ctx=self.submitter_ctx,
            note="submit",
        )
        self.service.approve_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=self.cosigner1_ctx,
            note="cosign 1",
        )
        self.service.approve_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=self.cosigner2_ctx,
            note="cosign 2",
        )
        self.service.approve_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=self.standardizer_ctx,
            note="standardize ok",
        )
        self.service.approve_revision_approval_step(
            controlled_revision_id=controlled_revision_id,
            ctx=self.approver_ctx,
            note="approve",
        )

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

    def test_submit_approve_workflow_and_audit_events(self):
        created = self.service.create_document(
            doc_code="DOC-001",
            title="Quality URS",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("urs.pdf", b"%PDF-1.4 urs\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="initial baseline",
        )

        self.assertEqual(created.target_kb_id, "kb-quality")
        self.assertEqual(created.target_kb_name, "Quality KB")
        self.assertEqual(created.current_revision.status, "draft")
        self.assertIsNone(created.effective_revision)

        revision1_id = created.current_revision.controlled_revision_id
        submitted = self.service.submit_revision_for_approval(
            controlled_revision_id=revision1_id,
            ctx=self.submitter_ctx,
            note="submit for approval",
        )
        self.assertEqual(submitted.current_revision.status, "approval_in_progress")
        self.assertIsNotNone(submitted.current_revision.approval_request_id)
        self.assertEqual(submitted.current_revision.current_approval_step_name, "cosign")
        self.assertEqual(submitted.current_revision.approval_round, 1)
        self.assertEqual(submitted.current_revision.file_subtype, "urs")
        self.assertIsInstance(submitted.current_revision.matrix_snapshot, dict)
        self.assertIsInstance(submitted.current_revision.position_snapshot, dict)
        self.assertEqual(submitted.current_revision.matrix_snapshot.get("file_subtype"), "urs")
        self.assertEqual(
            [item["position_name"] for item in submitted.current_revision.matrix_snapshot.get("approval_positions", []) if item.get("included")],
            ["编制部门负责人或授权代表"],
        )
        request_snapshot = self.service._approval_store.get_request(submitted.current_revision.approval_request_id)
        self.assertEqual(request_snapshot["workflow_snapshot"]["mode"], "approval_matrix")
        self.assertEqual(request_snapshot["workflow_snapshot"]["file_subtype"], "urs")
        self.assertIn("matrix_snapshot", request_snapshot["workflow_snapshot"])
        self.assertIn("position_snapshot", request_snapshot["workflow_snapshot"])

        after_cosign_1 = self.service.approve_revision_approval_step(
            controlled_revision_id=revision1_id,
            ctx=self.cosigner1_ctx,
            note="cosign 1",
        )
        self.assertEqual(after_cosign_1.current_revision.current_approval_step_name, "cosign")
        after_cosign_2 = self.service.approve_revision_approval_step(
            controlled_revision_id=revision1_id,
            ctx=self.cosigner2_ctx,
            note="cosign 2",
        )
        self.assertEqual(after_cosign_2.current_revision.current_approval_step_name, "standardize_review")

        after_standardize = self.service.approve_revision_approval_step(
            controlled_revision_id=revision1_id,
            ctx=self.standardizer_ctx,
            note="standardize ok",
        )
        self.assertEqual(after_standardize.current_revision.current_approval_step_name, "approve")

        final_doc = self.service.approve_revision_approval_step(
            controlled_revision_id=revision1_id,
            ctx=self.approver_ctx,
            note="approve",
        )
        self.assertEqual(final_doc.current_revision.status, "approved_pending_effective")
        self.assertIsNone(final_doc.current_revision.approval_request_id)
        self.assertEqual(final_doc.current_revision.current_approval_step_name, "approve")

        _, audit_events = self.audit_log_store.list_events(
            action="document_control_transition",
            resource_type="controlled_revision",
            limit=50,
        )
        event_types = [item.event_type for item in audit_events]
        self.assertIn("controlled_revision_submit", event_types)
        self.assertIn("controlled_revision_step_activated", event_types)
        self.assertIn("controlled_revision_step_approved", event_types)

    def test_submit_fails_when_compiler_position_does_not_include_applicant(self):
        created = self.service.create_document(
            doc_code="DOC-001A",
            title="Compiler mismatch",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("compiler-mismatch.pdf", b"%PDF-1.4 compiler mismatch\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        original_service = self.deps.quality_system_config_service
        self.deps.quality_system_config_service = SimpleNamespace(
            get_config=lambda: {
                "positions": [
                    {"name": "项目负责人", "assigned_users": [{"user_id": "someone-else", "username": "other"}]},
                    {"name": "QA", "assigned_users": [{"user_id": "cosigner-1", "username": "cosigner1"}]},
                    {"name": "文档管理员", "assigned_users": [{"user_id": "standardizer-1", "username": "standardizer"}]},
                    {"name": "编制部门负责人或授权代表", "assigned_users": [{"user_id": "approver-1", "username": "approver"}]},
                ]
            }
        )
        try:
            with self.assertRaises(DocumentControlError) as compiler_mismatch:
                self.service.submit_revision_for_approval(
                    controlled_revision_id=revision_id,
                    ctx=self.submitter_ctx,
                    note="submit",
                )
        finally:
            self.deps.quality_system_config_service = original_service
        self.assertEqual(compiler_mismatch.exception.code, "document_control_matrix_compiler_mismatch")
        self.assertEqual(compiler_mismatch.exception.status_code, 409)

    def test_submit_fails_when_required_position_has_no_assignees(self):
        created = self.service.create_document(
            doc_code="DOC-001B",
            title="Unassigned matrix position",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("matrix-unassigned.pdf", b"%PDF-1.4 matrix unassigned\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        original_service = self.deps.quality_system_config_service
        self.deps.quality_system_config_service = SimpleNamespace(
            get_config=lambda: {
                "positions": [
                    {"name": "项目负责人", "assigned_users": [{"user_id": "reviewer-1", "username": "reviewer"}]},
                    {"name": "QA", "assigned_users": []},
                    {"name": "文档管理员", "assigned_users": [{"user_id": "standardizer-1", "username": "standardizer"}]},
                    {"name": "编制部门负责人或授权代表", "assigned_users": [{"user_id": "approver-1", "username": "approver"}]},
                ]
            }
        )
        try:
            with self.assertRaises(DocumentControlError) as unassigned_position:
                self.service.submit_revision_for_approval(
                    controlled_revision_id=revision_id,
                    ctx=self.submitter_ctx,
                    note="submit",
                )
        finally:
            self.deps.quality_system_config_service = original_service
        self.assertEqual(unassigned_position.exception.code, "document_control_matrix_position_unassigned:QA")
        self.assertEqual(unassigned_position.exception.status_code, 409)

    def test_publish_rejects_when_not_approved_pending_effective(self):
        self._seed_doc_review_training_gate(user_id="docctrl-1", role_code="doc_control")
        created = self.service.create_document(
            doc_code="DOC-020",
            title="Publish gate",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("publish.pdf", b"%PDF-1.4 publish\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        with self.assertRaises(DocumentControlError) as invalid_status:
            self.service.publish_revision(
                controlled_revision_id=revision_id,
                release_mode="manual_by_doc_control",
                ctx=self.publisher_ctx,
                note="publish without approval",
            )
        self.assertEqual(invalid_status.exception.code, "document_control_publish_invalid_status")
        self.assertEqual(invalid_status.exception.status_code, 409)

    def test_publish_fail_fast_when_training_gate_not_configured(self):
        created = self.service.create_document(
            doc_code="DOC-021",
            title="Training gate",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("training.pdf", b"%PDF-1.4 training\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self._approve_revision_to_pending_effective(controlled_revision_id=revision_id)
        with self.assertRaises(DocumentControlError) as missing_gate:
            self.service.publish_revision(
                controlled_revision_id=revision_id,
                release_mode="manual_by_doc_control",
                ctx=self.publisher_ctx,
                note="publish should be blocked",
            )
        self.assertEqual(missing_gate.exception.code, "document_control_training_gate_not_configured")
        self.assertEqual(missing_gate.exception.status_code, 409)

    def test_publish_fail_fast_when_training_gate_requires_assignments(self):
        created = self.service.create_document(
            doc_code="DOC-021B",
            title="Training gate pending assignment",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("training-pending.pdf", b"%PDF-1.4 training\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self._approve_revision_to_pending_effective(controlled_revision_id=revision_id)
        self._configure_revision_training_gate(controlled_revision_id=revision_id, training_required=True)
        with self.assertRaises(DocumentControlError) as missing_assignments:
            self.service.publish_revision(
                controlled_revision_id=revision_id,
                release_mode="manual_by_doc_control",
                ctx=self.publisher_ctx,
                note="publish should be blocked",
            )
        self.assertEqual(missing_assignments.exception.code, "document_control_training_pending_assignment")
        self.assertEqual(missing_assignments.exception.status_code, 409)

    def test_publish_writes_release_ledger_and_supersedes_previous_effective(self):
        self._seed_doc_review_training_gate(user_id="docctrl-1", role_code="doc_control")
        created = self.service.create_document(
            doc_code="DOC-022",
            title="Release ledger",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("ledger.pdf", b"%PDF-1.4 ledger\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        self._seed_active_user(user_id="dept10-user-1", username="dept10-user-1", department_id=10)
        self.service.set_document_distribution_departments(
            controlled_document_id=created.controlled_document_id,
            department_ids=[10],
            ctx=self.submitter_ctx,
        )

        revision1_id = created.current_revision.controlled_revision_id
        self._approve_revision_to_pending_effective(controlled_revision_id=revision1_id)
        self._configure_revision_training_gate(controlled_revision_id=revision1_id, training_required=False)
        published_1 = self.service.publish_revision(
            controlled_revision_id=revision1_id,
            release_mode="manual_by_doc_control",
            ctx=self.publisher_ctx,
            note="publish v1",
        )
        self.assertEqual(published_1.effective_revision.controlled_revision_id, revision1_id)
        self.assertEqual(published_1.effective_revision.status, "effective")

        revised = self.service.create_revision(
            controlled_document_id=created.controlled_document_id,
            created_by="reviewer-1",
            upload_file=_UploadFile("ledger-v2.pdf", b"%PDF-1.4 ledger v2\n"),
            change_summary="update",
        )
        revision2_id = revised.current_revision.controlled_revision_id
        self._approve_revision_to_pending_effective(controlled_revision_id=revision2_id)
        self._configure_revision_training_gate(controlled_revision_id=revision2_id, training_required=False)
        published_2 = self.service.publish_revision(
            controlled_revision_id=revision2_id,
            release_mode="manual_by_doc_control",
            ctx=self.publisher_ctx,
            note="publish v2",
        )
        self.assertEqual(published_2.effective_revision.controlled_revision_id, revision2_id)
        self.assertEqual(published_2.effective_revision.status, "effective")

        revision1 = next(item for item in published_2.revisions if item.controlled_revision_id == revision1_id)
        revision2 = next(item for item in published_2.revisions if item.controlled_revision_id == revision2_id)
        self.assertEqual(revision1.status, "superseded")
        self.assertIsNotNone(revision1.superseded_at_ms)
        self.assertEqual(revision1.superseded_by_revision_id, revision2_id)
        self.assertEqual(revision2.status, "effective")

        self.assertEqual(len(self.ragflow_service.deleted), 1)

        conn = connect_sqlite(self._db_path)
        try:
            effective_count = conn.execute(
                "SELECT COUNT(*) AS count FROM controlled_revisions WHERE status = 'effective'"
            ).fetchone()["count"]
            ledger_count = conn.execute(
                "SELECT COUNT(*) AS count FROM controlled_revision_release_ledger"
            ).fetchone()["count"]
            ledger_rows = conn.execute(
                """
                SELECT event_type, release_mode, subject_revision_id, other_revision_id
                FROM controlled_revision_release_ledger
                ORDER BY created_at_ms ASC, ledger_id ASC
                """
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual(effective_count, 1)
        self.assertEqual(ledger_count, 3)
        self.assertTrue(all(row["release_mode"] == "manual_by_doc_control" for row in ledger_rows))
        published_rows = [row for row in ledger_rows if row["event_type"] == "published"]
        superseded_rows = [row for row in ledger_rows if row["event_type"] == "superseded"]
        self.assertEqual(len(published_rows), 2)
        self.assertEqual(len(superseded_rows), 1)
        supersede_row = superseded_rows[0]
        self.assertEqual(supersede_row["subject_revision_id"], revision1_id)
        self.assertEqual(supersede_row["other_revision_id"], revision2_id)
        published_by_subject = {row["subject_revision_id"]: row for row in published_rows}
        self.assertIn(revision1_id, published_by_subject)
        self.assertIn(revision2_id, published_by_subject)
        self.assertIsNone(published_by_subject[revision1_id]["other_revision_id"])
        self.assertEqual(published_by_subject[revision2_id]["other_revision_id"], revision1_id)

    def test_reviewer_and_approver_must_be_different_users(self):
        created = self.service.create_document(
            doc_code="DOC-010",
            title="Approval Separation",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("approval.pdf", b"%PDF-1.4 approval\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )

        revision_id = created.current_revision.controlled_revision_id
        self.service.submit_revision_for_approval(
            controlled_revision_id=revision_id,
            ctx=self.submitter_ctx,
            note="submit for approval",
        )

        with self.assertRaises(DocumentControlError) as same_actor_error:
            self.service.approve_revision_approval_step(controlled_revision_id=revision_id, ctx=self.submitter_ctx, note="same actor approval")

        self.assertEqual(same_actor_error.exception.code, "document_control_approval_role_conflict")
        self.assertEqual(same_actor_error.exception.status_code, 409)

    def test_reject_terminates_and_resubmit_creates_new_request(self):
        created = self.service.create_document(
            doc_code="DOC-020",
            title="Reject flow",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("reject.pdf", b"%PDF-1.4 reject\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        submitted = self.service.submit_revision_for_approval(
            controlled_revision_id=revision_id,
            ctx=self.submitter_ctx,
            note="submit",
        )
        first_request_id = submitted.current_revision.approval_request_id
        self.assertIsNotNone(first_request_id)

        rejected = self.service.reject_revision_approval_step(
            controlled_revision_id=revision_id,
            ctx=self.cosigner1_ctx,
            note="reject",
        )
        self.assertEqual(rejected.current_revision.status, "approval_rejected")
        self.assertIsNone(rejected.current_revision.approval_request_id)

        resubmitted = self.service.submit_revision_for_approval(
            controlled_revision_id=revision_id,
            ctx=self.submitter_ctx,
            note="resubmit",
        )
        self.assertEqual(resubmitted.current_revision.status, "approval_in_progress")
        self.assertEqual(resubmitted.current_revision.approval_round, 2)
        self.assertNotEqual(resubmitted.current_revision.approval_request_id, first_request_id)

        _, audit_events = self.audit_log_store.list_events(
            action="document_control_transition",
            resource_type="controlled_revision",
            limit=50,
        )
        event_types = [item.event_type for item in audit_events]
        self.assertIn("controlled_revision_step_rejected", event_types)
        self.assertIn("controlled_revision_resubmitted", event_types)

    def test_add_sign_requires_new_approver_to_participate(self):
        created = self.service.create_document(
            doc_code="DOC-030",
            title="Add sign flow",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("add-sign.pdf", b"%PDF-1.4 add sign\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self.service.submit_revision_for_approval(controlled_revision_id=revision_id, ctx=self.submitter_ctx, note="submit")

        self.service.approve_revision_approval_step(controlled_revision_id=revision_id, ctx=self.cosigner1_ctx, note="cosign 1")
        self.service.add_sign_revision_approval_step(
            controlled_revision_id=revision_id,
            approver_user_id="cosigner-3",
            ctx=self.cosigner1_ctx,
            note="add cosigner-3",
        )

        after_cosign_2 = self.service.approve_revision_approval_step(
            controlled_revision_id=revision_id,
            ctx=self.cosigner2_ctx,
            note="cosign 2",
        )
        self.assertEqual(after_cosign_2.current_revision.current_approval_step_name, "cosign")

        after_cosign_3 = self.service.approve_revision_approval_step(
            controlled_revision_id=revision_id,
            ctx=self.cosigner3_ctx,
            note="cosign 3",
        )
        self.assertEqual(after_cosign_3.current_revision.current_approval_step_name, "standardize_review")

    def test_add_sign_rejects_duplicate_and_forbidden_actor(self):
        created = self.service.create_document(
            doc_code="DOC-031",
            title="Add sign duplicate",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("add-sign-dup.pdf", b"%PDF-1.4 add sign\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self.service.submit_revision_for_approval(controlled_revision_id=revision_id, ctx=self.submitter_ctx, note="submit")

        with self.assertRaises(DocumentControlError) as forbidden:
            self.service.add_sign_revision_approval_step(
                controlled_revision_id=revision_id,
                approver_user_id="cosigner-3",
                ctx=self.submitter_ctx,
                note="not a step approver",
            )
        self.assertEqual(forbidden.exception.code, "document_control_add_sign_forbidden")
        self.assertEqual(forbidden.exception.status_code, 403)

        with self.assertRaises(DocumentControlError) as duplicated:
            self.service.add_sign_revision_approval_step(
                controlled_revision_id=revision_id,
                approver_user_id="cosigner-2",
                ctx=self.cosigner1_ctx,
                note="duplicate",
            )
        self.assertEqual(duplicated.exception.code, "document_control_add_sign_duplicated")
        self.assertEqual(duplicated.exception.status_code, 409)

    def test_submit_fail_fast_when_matrix_or_user_store_missing(self):
        created = self.service.create_document(
            doc_code="DOC-040",
            title="Missing prereqs",
            document_type="custom-missing-workflow",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("missing.pdf", b"%PDF-1.4 prereq\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id

        deps_no_matrix = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=self.ragflow_service,
            audit_log_store=self.audit_log_store,
            org_structure_manager=None,
            user_store=self.user_store,
            document_control_matrix_json_path=os.path.join(str(self._temp_dir), "missing-matrix.json"),
            quality_system_config_service=self.deps.quality_system_config_service,
        )
        service_no_matrix = DocumentControlService.from_deps(deps_no_matrix)
        with self.assertRaises(DocumentControlError) as missing_matrix:
            service_no_matrix.submit_revision_for_approval(controlled_revision_id=revision_id, ctx=self.submitter_ctx, note="submit")
        self.assertEqual(missing_matrix.exception.code, "document_control_matrix_missing")
        self.assertEqual(missing_matrix.exception.status_code, 500)

        created_configured = self.service.create_document(
            doc_code="DOC-041",
            title="Missing user store",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("missing-user-store.pdf", b"%PDF-1.4 prereq\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        configured_revision_id = created_configured.current_revision.controlled_revision_id

        deps_no_user_store = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=self.ragflow_service,
            audit_log_store=self.audit_log_store,
            org_structure_manager=None,
            document_control_matrix_json_path=self._matrix_path,
        )
        service_no_user_store = DocumentControlService.from_deps(deps_no_user_store)
        with self.assertRaises(DocumentControlError) as missing_user_store:
            service_no_user_store.submit_revision_for_approval(
                controlled_revision_id=configured_revision_id,
                ctx=self.submitter_ctx,
                note="submit",
            )
        self.assertEqual(missing_user_store.exception.code, "document_control_user_store_unavailable")
        self.assertEqual(missing_user_store.exception.status_code, 500)

    def test_document_type_workflow_is_persisted_and_resolved(self):
        workflow = self.service.upsert_document_type_workflow(
            document_type="manual",
            name="manual workflow",
            steps=[
                {
                    "step_type": "cosign",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 30,
                    "approver_user_ids": ["cosigner-1"],
                },
                {
                    "step_type": "approve",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 45,
                    "approver_user_ids": ["approver-1"],
                },
                {
                    "step_type": "standardize_review",
                    "approval_rule": "all",
                    "member_source": "fixed",
                    "timeout_reminder_minutes": 60,
                    "approver_user_ids": ["standardizer-1"],
                },
            ],
        )
        self.assertEqual(workflow["document_type"], "manual")
        loaded = self.service.get_document_type_workflow(document_type="manual")
        self.assertEqual([item["step_type"] for item in loaded["steps"]], ["cosign", "approve", "standardize_review"])
        self.assertEqual(loaded["steps"][0]["timeout_reminder_minutes"], 30)

    def test_remind_overdue_approval_step_marks_revision_and_returns_pending_approvers(self):
        created = self.service.create_document(
            doc_code="DOC-050",
            title="Reminder flow",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("reminder.pdf", b"%PDF-1.4 reminder\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )
        revision_id = created.current_revision.controlled_revision_id
        self.service.submit_revision_for_approval(
            controlled_revision_id=revision_id,
            ctx=self.submitter_ctx,
            note="submit",
        )
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

        result = self.service.remind_overdue_revision_approval_step(
            controlled_revision_id=revision_id,
            ctx=self.submitter_ctx,
            note="overdue reminder",
        )
        self.assertEqual(result["count"], 2)
        refreshed = self.service.get_document(controlled_document_id=created.controlled_document_id).current_revision
        self.assertIsNotNone(refreshed.current_approval_step_last_reminded_at_ms)
        self.assertIsNotNone(refreshed.current_approval_step_overdue_at_ms)

    def test_create_document_rejects_non_pdf_upload(self):
        with self.assertRaises(DocumentControlError) as non_pdf:
            self.service.create_document(
                doc_code="DOC-060",
                title="Non PDF",
                document_type="sop",
                target_kb_id="Quality KB",
                created_by="reviewer-1",
                upload_file=_UploadFile("not-pdf.md", b"# not pdf\n", content_type="text/markdown"),
                product_name="Product A",
                registration_ref="REG-001",
            )
        self.assertEqual(non_pdf.exception.code, "document_control_pdf_required")
        self.assertEqual(non_pdf.exception.status_code, 400)

    def test_duplicate_doc_code_returns_conflict_error(self):
        self.service.create_document(
            doc_code="DOC-001",
            title="Quality URS",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("urs.pdf", b"%PDF-1.4 urs\n"),
            product_name="Product A",
            registration_ref="REG-001",
        )

        with self.assertRaises(DocumentControlError) as ctx:
            self.service.create_document(
                doc_code="DOC-001",
                title="Another URS",
                document_type="urs",
                target_kb_id="Quality KB",
                created_by="reviewer-1",
                upload_file=_UploadFile("urs-copy.pdf", b"%PDF-1.4 urs copy\n"),
                product_name="Product A",
                registration_ref="REG-001",
            )

        self.assertEqual(ctx.exception.code, "doc_code_conflict")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_create_document_requires_product_metadata_and_allows_empty_registration_ref(self):
        with self.assertRaises(DocumentControlError) as missing_product:
            self.service.create_document(
                doc_code="DOC-002",
                title="Quality SRS",
                document_type="srs",
                target_kb_id="Quality KB",
                created_by="reviewer-1",
                upload_file=_UploadFile("srs.pdf", b"%PDF-1.4 srs\n"),
                product_name="",
                registration_ref="REG-001",
            )

        self.assertEqual(missing_product.exception.code, "product_name_required")
        self.assertEqual(missing_product.exception.status_code, 400)

        document = self.service.create_document(
            doc_code="DOC-003",
            title="Quality WI",
            document_type="wi",
            file_subtype="工艺流程图",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("wi.pdf", b"%PDF-1.4 wi\n"),
            product_name="Product A",
            registration_ref="",
        )

        self.assertEqual(document.registration_ref, None)
        self.assertEqual(document.file_subtype, "工艺流程图")


if __name__ == "__main__":
    unittest.main()
