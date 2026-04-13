import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from backend.app.core.permission_resolver import PermissionSnapshot, ResourceScope
from backend.app.modules.knowledge.routes.documents import list_documents
from backend.app.modules.knowledge.routes.versions import list_document_versions
from backend.database.schema.ensure import ensure_schema
from backend.services.electronic_signature import ElectronicSignatureService, ElectronicSignatureStore
from backend.services.kb import KbStore
from backend.services.users import hash_password
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _snapshot(kb_id: str) -> PermissionSnapshot:
    return PermissionSnapshot(
        is_admin=False,
        can_upload=False,
        can_review=True,
        can_download=True,
        can_copy=False,
        can_delete=False,
        can_manage_kb_directory=False,
        can_view_kb_config=False,
        can_view_tools=False,
        kb_scope=ResourceScope.SET,
        kb_names=frozenset({kb_id}),
        chat_scope=ResourceScope.NONE,
        chat_ids=frozenset(),
        tool_scope=ResourceScope.NONE,
        tool_ids=frozenset(),
    )


class _UserStore:
    def get_usernames_by_ids(self, user_ids):
        return {user_id: f"user-{user_id}" for user_id in user_ids if user_id}


class TestDocumentVersioningUnit(unittest.TestCase):
    def test_version_chain_keeps_old_record_and_exposes_history(self):
        td = make_temp_dir(prefix="ragflowauth_doc_versions")
        try:
            repo_root = td / "repo"
            uploads_root = repo_root / "data" / "uploads" / "doc-versioning"
            uploads_root.mkdir(parents=True, exist_ok=True)
            db_path = repo_root / "data" / "auth.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

            with mock.patch("backend.app.core.managed_paths.repo_root", return_value=repo_root):
                ensure_schema(db_path)
                kb_store = KbStore(db_path=str(db_path))
                signature_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=str(db_path)))
                signer = SimpleNamespace(
                    user_id="reviewer-1",
                    username="qa-reviewer",
                    status="active",
                    password_hash=hash_password("SignPass123"),
                )

                old_path = uploads_root / "same_v1.txt"
                new_path = uploads_root / "same_v2.txt"
                old_path.write_text("version one", encoding="utf-8")
                new_path.write_text("version two", encoding="utf-8")

                old_doc = kb_store.create_document(
                    filename="same.txt",
                    file_path=str(old_path),
                    file_size=old_path.stat().st_size,
                    mime_type="text/plain",
                    uploaded_by="uploader-1",
                    kb_id="kb-a",
                    kb_dataset_id="ds-a",
                    kb_name="kb-a",
                    status="approved",
                )
                old_doc = kb_store.update_document_status(
                    doc_id=old_doc.doc_id,
                    status="approved",
                    reviewed_by="reviewer-1",
                    review_notes="seed approved",
                    ragflow_doc_id="rag-old-1",
                )

                new_doc = kb_store.create_document(
                    filename="same.txt",
                    file_path=str(new_path),
                    file_size=new_path.stat().st_size,
                    mime_type="text/plain",
                    uploaded_by="uploader-1",
                    kb_id="kb-a",
                    kb_dataset_id="ds-a",
                    kb_name="kb-a",
                    status="pending",
                )
                new_doc = kb_store.update_document_status(
                    doc_id=new_doc.doc_id,
                    status="approved",
                    reviewed_by="reviewer-2",
                    review_notes="approved as replacement",
                    ragflow_doc_id="rag-new-1",
                )

                old_sign = signature_service.issue_challenge(user=signer, password="SignPass123")
                old_ctx = signature_service.consume_sign_token(
                    user=signer,
                    sign_token=old_sign["sign_token"],
                    action="document_approve",
                )
                signature_service.create_signature(
                    signing_context=old_ctx,
                    user=signer,
                    record_type="knowledge_document_review",
                    record_id=old_doc.doc_id,
                    action="document_approve",
                    meaning="Document approval",
                    reason="Approved initial version",
                    record_payload={"doc_id": old_doc.doc_id, "status": "approved"},
                )

                new_sign = signature_service.issue_challenge(user=signer, password="SignPass123")
                new_ctx = signature_service.consume_sign_token(
                    user=signer,
                    sign_token=new_sign["sign_token"],
                    action="document_supersede",
                )
                expected_new_signature = signature_service.create_signature(
                    signing_context=new_ctx,
                    user=signer,
                    record_type="knowledge_document_review",
                    record_id=new_doc.doc_id,
                    action="document_supersede",
                    meaning="Supersede approval",
                    reason="Approved replacement version",
                    record_payload={"doc_id": new_doc.doc_id, "status": "approved"},
                )

                old_after, new_after = kb_store.apply_version_replacement(
                    old_doc_id=old_doc.doc_id,
                    new_doc_id=new_doc.doc_id,
                    effective_status="approved",
                )

                self.assertIsNotNone(old_after)
                self.assertIsNotNone(new_after)
                self.assertFalse(old_after.is_current)
                self.assertEqual(old_after.effective_status, "superseded")
                self.assertEqual(old_after.superseded_by_doc_id, new_after.doc_id)
                self.assertTrue(Path(old_after.file_path).exists())
                self.assertEqual(old_after.version_no, 1)

                self.assertTrue(new_after.is_current)
                self.assertEqual(new_after.effective_status, "approved")
                self.assertEqual(new_after.previous_doc_id, old_after.doc_id)
                self.assertEqual(new_after.version_no, 2)
                self.assertEqual(new_after.logical_doc_id, old_after.logical_doc_id)
                self.assertEqual(len(new_after.file_sha256 or ""), 64)

                self.assertEqual(kb_store.count_documents(status="approved"), 1)
                self.assertEqual(kb_store.get_current_document(old_after.doc_id).doc_id, new_after.doc_id)

                versions = kb_store.list_versions(new_after.doc_id)
                self.assertEqual([item.doc_id for item in versions], [new_after.doc_id, old_after.doc_id])
                self.assertEqual([item.version_no for item in versions], [2, 1])

                ctx = SimpleNamespace(
                    deps=SimpleNamespace(
                        kb_store=kb_store,
                        user_store=_UserStore(),
                        electronic_signature_service=signature_service,
                    ),
                    user=SimpleNamespace(username="auditor", role="reviewer"),
                    snapshot=_snapshot("kb-a"),
                )
                docs_payload = list_documents(ctx, status="approved", kb_id="kb-a", limit=10)
                self.assertEqual(docs_payload["count"], 1)
                self.assertEqual(docs_payload["documents"][0]["signature_id"], expected_new_signature.signature_id)
                self.assertEqual(docs_payload["documents"][0]["signature_meaning"], "Supersede approval")
                self.assertEqual(docs_payload["documents"][0]["signature_reason"], "Approved replacement version")
                self.assertEqual(docs_payload["documents"][0]["signed_by_username"], "qa-reviewer")
                self.assertTrue(docs_payload["documents"][0]["signature_verified"])

                payload = list_document_versions(new_after.doc_id, ctx)
                self.assertEqual(payload["logical_doc_id"], new_after.logical_doc_id)
                self.assertEqual(payload["current_doc_id"], new_after.doc_id)
                self.assertEqual(payload["count"], 2)
                self.assertEqual(payload["versions"][0]["version_no"], 2)
                self.assertEqual(payload["versions"][1]["effective_status"], "superseded")
                self.assertEqual(payload["versions"][0]["signature_id"], expected_new_signature.signature_id)
                self.assertEqual(payload["versions"][0]["signature_action"], "document_supersede")
                self.assertEqual(payload["versions"][0]["signature_meaning"], "Supersede approval")
                self.assertTrue(payload["versions"][0]["signature_verified"])
                self.assertTrue(payload["versions"][1]["signature_verified"])
                self.assertEqual(payload["versions"][1]["signature_reason"], "Approved initial version")
                self.assertEqual(
                    json.loads(json.dumps(payload["versions"][0]))["file_sha256"],
                    new_after.file_sha256,
                )
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
