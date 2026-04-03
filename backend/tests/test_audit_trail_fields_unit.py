import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestAuditTrailFieldsUnit(unittest.TestCase):
    def test_chain_fields_and_filters(self):
        td = make_temp_dir(prefix="ragflowauth_audit_fields")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = AuditLogStore(db_path=db_path)

            e1 = store.log_event(
                action="document_approve",
                actor="u1",
                source="review",
                resource_type="knowledge_document",
                resource_id="doc-1",
                event_type="update",
                before={"status": "pending"},
                after={"status": "approved"},
                reason="approve_review",
                signature_id="sig-1",
                request_id="rid-1",
                client_ip="10.0.0.1",
                doc_id="doc-1",
                filename="a.pdf",
                kb_id="kb-a",
                kb_dataset_id="ds-a",
                kb_name="kb-a",
            )
            e2 = store.log_event(
                action="document_reject",
                actor="u2",
                source="review",
                resource_type="knowledge_document",
                resource_id="doc-2",
                event_type="update",
                before={"status": "pending"},
                after={"status": "rejected"},
                reason="reject_review",
                signature_id="sig-2",
                request_id="rid-2",
                client_ip="10.0.0.2",
                doc_id="doc-2",
                filename="b.pdf",
                kb_id="kb-b",
                kb_dataset_id="ds-b",
                kb_name="kb-b",
            )

            self.assertIsNotNone(e1.event_hash)
            self.assertEqual(len(str(e1.event_hash)), 64)
            self.assertIsNone(e1.prev_hash)
            self.assertEqual(e2.prev_hash, e1.event_hash)

            total, rows = store.list_events(
                resource_type="knowledge_document",
                resource_id="doc-1",
                event_type="update",
                signature_id="sig-1",
                request_id="rid-1",
            )
            self.assertEqual(total, 1)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.action, "document_approve")
            self.assertEqual(row.reason, "approve_review")
            self.assertEqual(row.client_ip, "10.0.0.1")
            self.assertIn('"status":"pending"', row.before_json or "")
            self.assertIn('"status":"approved"', row.after_json or "")
        finally:
            cleanup_dir(td)
