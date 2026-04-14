import io
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
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _UploadFile:
    def __init__(self, filename: str, content: bytes, content_type: str = "text/markdown"):
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

    def delete_document(self, doc_id: str):
        conn = connect_sqlite(self.db_path)
        try:
            conn.execute("DELETE FROM kb_documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
        finally:
            conn.close()
        return True


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


class TestDocumentControlServiceUnit(unittest.TestCase):
    def setUp(self):
        self._temp_dir = make_temp_dir(prefix="ragflowauth_doc_control_service")
        self._db_path = os.path.join(str(self._temp_dir), "auth.db")
        self._old_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = str(Path(self._temp_dir) / "uploads")
        ensure_schema(self._db_path)
        self.audit_log_store = AuditLogStore(db_path=self._db_path)
        self.ragflow_service = _RagflowService()
        self.deps = SimpleNamespace(
            kb_store=_KbStore(self._db_path),
            ragflow_service=self.ragflow_service,
            audit_log_store=self.audit_log_store,
            org_structure_manager=None,
        )
        self.service = DocumentControlService.from_deps(self.deps)
        self.ctx = SimpleNamespace(
            payload=SimpleNamespace(sub="reviewer-1"),
            user=SimpleNamespace(
                user_id="reviewer-1",
                username="reviewer",
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

    def tearDown(self):
        settings.UPLOAD_DIR = self._old_upload_dir
        cleanup_dir(self._temp_dir)

    def test_create_document_lifecycle_and_revision_rollover(self):
        created = self.service.create_document(
            doc_code="DOC-001",
            title="Quality URS",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("urs.md", b"# urs\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="initial baseline",
        )

        self.assertEqual(created.target_kb_id, "kb-quality")
        self.assertEqual(created.target_kb_name, "Quality KB")
        self.assertEqual(created.current_revision.status, "draft")
        self.assertIsNone(created.effective_revision)

        revision1_id = created.current_revision.controlled_revision_id
        self.service.transition_revision(
            controlled_revision_id=revision1_id,
            target_status="in_review",
            ctx=self.ctx,
            note="submit for review",
        )
        self.service.transition_revision(
            controlled_revision_id=revision1_id,
            target_status="approved",
            ctx=self.approver_ctx,
            note="approved",
        )
        effective_first = self.service.transition_revision(
            controlled_revision_id=revision1_id,
            target_status="effective",
            ctx=self.approver_ctx,
            note="release",
        )

        self.assertEqual(effective_first.current_revision.status, "effective")
        self.assertEqual(effective_first.effective_revision.status, "effective")
        self.assertEqual(effective_first.current_revision.reviewed_by, "reviewer-1")
        self.assertEqual(effective_first.current_revision.approved_by, "approver-1")

        revised = self.service.create_revision(
            controlled_document_id=created.controlled_document_id,
            created_by="reviewer-1",
            upload_file=_UploadFile("urs-v2.md", b"# urs v2\n"),
            change_summary="update requirements",
        )
        revision2_id = revised.current_revision.controlled_revision_id
        self.assertNotEqual(revision2_id, revision1_id)
        self.assertEqual(revised.current_revision.status, "draft")
        self.assertEqual(revised.effective_revision.controlled_revision_id, revision1_id)

        self.service.transition_revision(
            controlled_revision_id=revision2_id,
            target_status="in_review",
            ctx=self.ctx,
            note="review v2",
        )
        self.service.transition_revision(
            controlled_revision_id=revision2_id,
            target_status="approved",
            ctx=self.approver_ctx,
            note="approve v2",
        )
        effective_second = self.service.transition_revision(
            controlled_revision_id=revision2_id,
            target_status="effective",
            ctx=self.approver_ctx,
            note="release v2",
        )

        self.assertEqual(effective_second.effective_revision.controlled_revision_id, revision2_id)
        self.assertEqual(effective_second.current_revision.controlled_revision_id, revision2_id)
        first_revision = next(
            item for item in effective_second.revisions if item.controlled_revision_id == revision1_id
        )
        second_revision = next(
            item for item in effective_second.revisions if item.controlled_revision_id == revision2_id
        )
        self.assertEqual(first_revision.status, "obsolete")
        self.assertEqual(second_revision.status, "effective")
        self.assertEqual(len(self.ragflow_service.deleted), 1)

        conn = connect_sqlite(self._db_path)
        try:
            effective_count = conn.execute(
                "SELECT COUNT(*) AS count FROM controlled_revisions WHERE status = 'effective'"
            ).fetchone()["count"]
        finally:
            conn.close()
        self.assertEqual(effective_count, 1)

        _, audit_events = self.audit_log_store.list_events(
            action="document_control_transition",
            resource_type="controlled_revision",
            limit=20,
        )
        event_types = [item.event_type for item in audit_events]
        self.assertIn("controlled_revision_effective", event_types)
        self.assertIn("controlled_revision_obsolete", event_types)

    def test_reviewer_and_approver_must_be_different_users(self):
        created = self.service.create_document(
            doc_code="DOC-010",
            title="Approval Separation",
            document_type="sop",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("approval.md", b"# approval\n"),
            product_name="Product A",
            registration_ref="REG-001",
            change_summary="baseline",
        )

        revision_id = created.current_revision.controlled_revision_id
        self.service.transition_revision(
            controlled_revision_id=revision_id,
            target_status="in_review",
            ctx=self.ctx,
            note="submit for review",
        )

        with self.assertRaises(DocumentControlError) as same_actor_error:
            self.service.transition_revision(
                controlled_revision_id=revision_id,
                target_status="approved",
                ctx=self.ctx,
                note="same actor approval",
            )

        self.assertEqual(same_actor_error.exception.code, "document_control_approval_role_conflict")
        self.assertEqual(same_actor_error.exception.status_code, 409)

    def test_duplicate_doc_code_returns_conflict_error(self):
        self.service.create_document(
            doc_code="DOC-001",
            title="Quality URS",
            document_type="urs",
            target_kb_id="Quality KB",
            created_by="reviewer-1",
            upload_file=_UploadFile("urs.md", b"# urs\n"),
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
                upload_file=_UploadFile("urs-copy.md", b"# urs copy\n"),
                product_name="Product A",
                registration_ref="REG-001",
            )

        self.assertEqual(ctx.exception.code, "doc_code_conflict")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_create_document_requires_product_and_registration_metadata(self):
        with self.assertRaises(DocumentControlError) as missing_product:
            self.service.create_document(
                doc_code="DOC-002",
                title="Quality SRS",
                document_type="srs",
                target_kb_id="Quality KB",
                created_by="reviewer-1",
                upload_file=_UploadFile("srs.md", b"# srs\n"),
                product_name="",
                registration_ref="REG-001",
            )

        self.assertEqual(missing_product.exception.code, "product_name_required")
        self.assertEqual(missing_product.exception.status_code, 400)

        with self.assertRaises(DocumentControlError) as missing_registration:
            self.service.create_document(
                doc_code="DOC-003",
                title="Quality WI",
                document_type="wi",
                target_kb_id="Quality KB",
                created_by="reviewer-1",
                upload_file=_UploadFile("wi.md", b"# wi\n"),
                product_name="Product A",
                registration_ref="",
            )

        self.assertEqual(missing_registration.exception.code, "registration_ref_required")
        self.assertEqual(missing_registration.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
