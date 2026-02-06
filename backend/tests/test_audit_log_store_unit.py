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

            store.log_event(
                action="auth_login",
                actor="u1",
                actor_username="alice",
                company_id=1,
                company_name="瑛泰",
                department_id=2,
                department_name="研发",
                source="auth",
                meta={"username": "alice"},
            )
            t0 = int(time.time() * 1000)
            store.log_event(
                action="document_preview",
                actor="u1",
                actor_username="alice",
                company_id=1,
                company_name="瑛泰",
                department_id=2,
                department_name="研发",
                source="ragflow",
                doc_id="d1",
                filename="a.pdf",
                kb_id="展厅",
                meta={"type": "pdf"},
            )
            t1 = int(time.time() * 1000)

            total, rows = store.list_events(limit=10)
            self.assertGreaterEqual(total, 2)
            self.assertGreaterEqual(len(rows), 2)
            self.assertEqual(rows[0].action, "document_preview")
            self.assertEqual(rows[1].action, "auth_login")

            total2, previews = store.list_events(action="document_preview")
            self.assertEqual(total2, 1)
            self.assertEqual(len(previews), 1)
            self.assertEqual(previews[0].doc_id, "d1")

            total3, rows3 = store.list_events(actor_username="alice", company_id=1, department_id=2)
            self.assertEqual(total3, 2)
            self.assertEqual(len(rows3), 2)

            total4, rows4 = store.list_events(from_ms=t0, to_ms=t1)
            self.assertGreaterEqual(total4, 1)
            self.assertTrue(all(r.created_at_ms >= t0 for r in rows4))
        finally:
            cleanup_dir(td)

