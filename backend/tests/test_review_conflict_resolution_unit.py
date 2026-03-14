import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from authx import TokenPayload
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.authz import AuthContext, get_auth_context
from backend.app.core.permission_resolver import ResourceScope
from backend.app.modules.review.router import router as review_router
from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.services.deletion_log_store import DeletionLogStore
from backend.services.kb_store import KbStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _FakeRagflowService:
    def delete_document(self, ragflow_doc_id: str, dataset_name: str | None = None):  # noqa: ARG002
        return bool(str(ragflow_doc_id or "").strip())

    def upload_document_blob(self, file_filename: str, file_content: bytes, kb_id: str = "kb1"):  # noqa: ARG002
        return "rg_uploaded"

    def parse_document(self, dataset_ref: str, document_id: str):  # noqa: ARG002
        return True


class _FakeUserStore:
    @staticmethod
    def get_usernames_by_ids(ids):  # noqa: A003
        return {str(item): f"user-{item}" for item in ids or []}


class TestReviewConflictResolutionUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_review_conflict")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

        self.kb_store = KbStore(db_path=self.db_path)
        self.audit_store = AuditLogStore(db_path=self.db_path)
        self.deletion_store = DeletionLogStore(db_path=self.db_path)
        self.deps = SimpleNamespace(
            kb_store=self.kb_store,
            audit_log_store=self.audit_store,
            deletion_log_store=self.deletion_store,
            ragflow_service=_FakeRagflowService(),
            user_store=_FakeUserStore(),
        )

        self.app = FastAPI()
        self.app.include_router(review_router, prefix="/api/knowledge")

    def tearDown(self):
        cleanup_dir(self._tmp)

    def _client(self) -> TestClient:
        ctx = AuthContext(
            deps=self.deps,
            payload=TokenPayload(sub="u1"),
            user=SimpleNamespace(user_id="u1", username="tester", company_id=None, department_id=None),
            snapshot=SimpleNamespace(
                is_admin=True,
                can_review=True,
                kb_scope=ResourceScope.ALL,
                kb_names=frozenset(),
            ),
        )
        self.app.dependency_overrides[get_auth_context] = lambda: ctx
        return TestClient(self.app)

    def _create_doc(
        self,
        *,
        filename: str,
        status: str = "pending",
        ragflow_doc_id: str | None = None,
        content: bytes | None = None,
    ):
        uploads_root = Path(self._tmp) / "uploads"
        uploads_root.mkdir(parents=True, exist_ok=True)
        path = uploads_root / filename
        path.write_bytes(content if content is not None else b"unit-test-content")
        doc = self.kb_store.create_document(
            filename=filename,
            file_path=str(path),
            file_size=path.stat().st_size,
            mime_type="application/pdf",
            uploaded_by="u1",
            kb_id="kb1",
            kb_dataset_id="kb1",
            kb_name="kb1",
            status="pending",
        )
        if status != "pending":
            doc = self.kb_store.update_document_status(
                doc_id=doc.doc_id,
                status=status,
                reviewed_by="u_admin",
                review_notes=f"seed_{status}",
                ragflow_doc_id=ragflow_doc_id,
            )
        return doc

    def test_overwrite_requires_reason(self):
        old_doc = self._create_doc(filename="paper.pdf", status="approved", ragflow_doc_id="rg_old_1")
        new_doc = self._create_doc(filename="paper(1).pdf", status="pending")

        with self._client() as client:
            resp = client.post(
                f"/api/knowledge/documents/{new_doc.doc_id}/approve-overwrite",
                json={"replace_doc_id": old_doc.doc_id},
            )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("detail"), "overwrite_reason_required")

    def test_list_conflicts_returns_pending_conflicts(self):
        self._create_doc(filename="paper.pdf", status="approved", ragflow_doc_id="rg_old_2")
        pending = self._create_doc(filename="paper(1).pdf", status="pending")

        with self._client() as client:
            resp = client.get("/api/knowledge/documents/conflicts?limit=20")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(int(payload.get("total") or 0), 1)
        item = (payload.get("items") or [])[0]
        self.assertEqual(((item.get("pending") or {}).get("doc_id")), pending.doc_id)

    def test_overwrite_records_structured_audit_reason(self):
        old_doc = self._create_doc(filename="paper.pdf", status="approved", ragflow_doc_id="rg_old_3")
        new_doc = self._create_doc(filename="paper(1).pdf", status="pending")

        with self._client() as client:
            resp = client.post(
                f"/api/knowledge/documents/{new_doc.doc_id}/approve-overwrite",
                json={
                    "replace_doc_id": old_doc.doc_id,
                    "overwrite_reason": "内容更新",
                },
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("status"), "approved")
        self.assertEqual(body.get("review_notes"), "内容更新")
        self.assertIsNone(self.kb_store.get_document(old_doc.doc_id))

        total, events = self.audit_store.list_events(action="document_conflict_resolved", limit=20)
        self.assertGreaterEqual(total, 1)
        meta = json.loads(str(events[0].meta_json or "{}"))
        self.assertEqual(meta.get("resolution"), "overwrite")
        self.assertEqual(meta.get("overwrite_reason"), "内容更新")

    def test_resolve_conflict_rename_updates_file_and_logs_audit(self):
        self._create_doc(filename="paper.pdf", status="approved", ragflow_doc_id="rg_old_4")
        pending = self._create_doc(filename="paper(1).pdf", status="pending")
        old_path = Path(str(pending.file_path))

        with self._client() as client:
            resp = client.post(
                f"/api/knowledge/documents/{pending.doc_id}/resolve-conflict-rename",
                json={
                    "target_filename": "paper_v2.pdf",
                    "rename_reason": "避免覆盖原稿",
                },
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("filename"), "paper_v2.pdf")
        renamed = self.kb_store.get_document(pending.doc_id)
        self.assertIsNotNone(renamed)
        self.assertTrue(Path(str(renamed.file_path)).exists())
        self.assertFalse(old_path.exists())

        total, events = self.audit_store.list_events(action="document_conflict_resolved", limit=20)
        self.assertGreaterEqual(total, 1)
        meta = json.loads(str(events[0].meta_json or "{}"))
        self.assertEqual(meta.get("resolution"), "rename")
        self.assertEqual(meta.get("reason"), "避免覆盖原稿")

    def test_resolve_conflict_skip_rejects_and_logs_audit(self):
        self._create_doc(filename="paper.pdf", status="approved", ragflow_doc_id="rg_old_5")
        pending = self._create_doc(filename="paper(1).pdf", status="pending")

        with self._client() as client:
            resp = client.post(
                f"/api/knowledge/documents/{pending.doc_id}/resolve-conflict-skip",
                json={"skip_reason": "保留历史版本"},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body.get("status"), "rejected")
        self.assertIn("保留历史版本", str(body.get("review_notes") or ""))

        total, events = self.audit_store.list_events(action="document_conflict_resolved", limit=20)
        self.assertGreaterEqual(total, 1)
        meta = json.loads(str(events[0].meta_json or "{}"))
        self.assertEqual(meta.get("resolution"), "skip")
        self.assertEqual(meta.get("reason"), "保留历史版本")

    def test_batch_approve_deduplicates_and_writes_batch_audit(self):
        first = self._create_doc(filename="batch_a_1.pdf", status="pending")
        second = self._create_doc(filename="batch_a_2.pdf", status="pending")

        with self._client() as client:
            resp = client.post(
                "/api/knowledge/documents/batch/approve",
                json={
                    "doc_ids": [first.doc_id, second.doc_id, first.doc_id],
                    "review_notes": "batch approve",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(int(payload.get("total") or 0), 3)
        self.assertEqual(int(payload.get("success_count") or 0), 2)
        self.assertEqual(int(payload.get("failed_count") or 0), 1)
        failed = payload.get("failed_items") or []
        self.assertEqual(str(failed[0].get("detail") or ""), "duplicate_doc_id_in_batch")

        total, events = self.audit_store.list_events(action="document_review_batch", limit=20)
        self.assertGreaterEqual(total, 1)
        meta = json.loads(str(events[0].meta_json or "{}"))
        self.assertEqual(meta.get("operation"), "approve")
        self.assertEqual(int(meta.get("duplicate_total") or 0), 1)
        self.assertEqual(int(meta.get("success_count") or 0), 2)

    def test_batch_reject_deduplicates_and_writes_batch_audit(self):
        first = self._create_doc(filename="batch_r_1.pdf", status="pending")
        second = self._create_doc(filename="batch_r_2.pdf", status="pending")

        with self._client() as client:
            resp = client.post(
                "/api/knowledge/documents/batch/reject",
                json={
                    "doc_ids": [first.doc_id, second.doc_id, first.doc_id],
                    "review_notes": "batch reject",
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(int(payload.get("total") or 0), 3)
        self.assertEqual(int(payload.get("success_count") or 0), 2)
        self.assertEqual(int(payload.get("failed_count") or 0), 1)
        failed = payload.get("failed_items") or []
        self.assertEqual(str(failed[0].get("detail") or ""), "duplicate_doc_id_in_batch")

        total, events = self.audit_store.list_events(action="document_review_batch", limit=20)
        self.assertGreaterEqual(total, 1)
        meta = json.loads(str(events[0].meta_json or "{}"))
        self.assertEqual(meta.get("operation"), "reject")
        self.assertEqual(int(meta.get("duplicate_total") or 0), 1)
        self.assertEqual(int(meta.get("success_count") or 0), 2)


if __name__ == "__main__":
    unittest.main()
