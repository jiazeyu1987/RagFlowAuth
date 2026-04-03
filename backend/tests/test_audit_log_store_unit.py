import os
import time
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestAuditLogStoreUnit(unittest.TestCase):
    def test_log_and_list_events(self):
        td = make_temp_dir(prefix="ragflowauth_audit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            store = AuditLogStore(db_path=db_path)

            login_event = store.log_event(
                action="auth_login",
                actor="u1",
                actor_username="alice",
                company_id=1,
                company_name="Acme",
                department_id=2,
                department_name="R&D",
                source="auth",
                meta={"username": "alice"},
            )
            t0 = int(time.time() * 1000)
            preview_event = store.log_event(
                action="document_preview",
                actor="u1",
                actor_username="alice",
                company_id=1,
                company_name="Acme",
                department_id=2,
                department_name="R&D",
                source="knowledge",
                doc_id="d1",
                filename="a.pdf",
                kb_id="kb-a",
                kb_dataset_id="ds-1",
                kb_name="kb-a",
                resource_type="knowledge_document",
                resource_id="d1",
                event_type="preview",
                before={"status": "approved"},
                after={"status": "approved"},
                reason="preview_check",
                signature_id="sig-preview",
                request_id="rid-preview",
                client_ip="127.0.0.1",
                meta={"type": "pdf"},
            )
            download_event = store.log_event(
                action="document_download",
                actor="u1",
                actor_username="alice",
                company_id=1,
                company_name="Acme",
                department_id=2,
                department_name="R&D",
                source="knowledge",
                doc_id="d2",
                filename="b.pdf",
                kb_id="kb-b",
                kb_dataset_id="ds-2",
                kb_name="kb-b",
                meta={},
            )
            t1 = int(time.time() * 1000)

            total, rows = store.list_events(limit=10)
            self.assertGreaterEqual(total, 3)
            self.assertGreaterEqual(len(rows), 3)
            actions = {r.action for r in rows}
            self.assertIn("auth_login", actions)
            self.assertIn("document_preview", actions)
            self.assertIn("document_download", actions)

            total2, previews = store.list_events(action="document_preview")
            self.assertEqual(total2, 1)
            self.assertEqual(len(previews), 1)
            self.assertEqual(previews[0].doc_id, "d1")
            self.assertEqual(previews[0].resource_type, "knowledge_document")
            self.assertEqual(previews[0].resource_id, "d1")
            self.assertEqual(previews[0].signature_id, "sig-preview")
            self.assertEqual(previews[0].request_id, "rid-preview")
            self.assertEqual(previews[0].reason, "preview_check")
            self.assertIsNotNone(previews[0].event_hash)
            self.assertEqual(preview_event.prev_hash, login_event.event_hash)
            self.assertEqual(download_event.prev_hash, preview_event.event_hash)

            total3, rows3 = store.list_events(actor_username="alice", company_id=1, department_id=2)
            self.assertEqual(total3, 3)
            self.assertEqual(len(rows3), 3)

            total4, rows4 = store.list_events(from_ms=t0, to_ms=t1)
            self.assertGreaterEqual(total4, 1)
            self.assertTrue(all(r.created_at_ms >= t0 for r in rows4))

            total5, rows5 = store.list_events(doc_id="d1")
            self.assertEqual(total5, 1)
            self.assertEqual(rows5[0].filename, "a.pdf")

            total6, rows6 = store.list_events(kb_dataset_id="ds-2")
            self.assertEqual(total6, 1)
            self.assertEqual(rows6[0].doc_id, "d2")

            total7, rows7 = store.list_events(filename="b.pdf", kb_name="kb-b")
            self.assertEqual(total7, 1)
            self.assertEqual(rows7[0].action, "document_download")
            self.assertEqual(rows7[0].meta_json, "{}")

            total8, rows8 = store.list_events(request_id="rid-preview", signature_id="sig-preview")
            self.assertEqual(total8, 1)
            self.assertEqual(rows8[0].resource_id, "d1")
        finally:
            cleanup_dir(td)
