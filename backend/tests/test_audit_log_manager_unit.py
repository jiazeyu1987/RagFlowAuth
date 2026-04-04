import os
import unittest
from types import SimpleNamespace

from backend.database.schema.ensure import ensure_schema
from backend.services.audit import AuditLogManager
from backend.services.audit_log_store import AuditLogStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _User:
    def __init__(self):
        self.user_id = "u1"
        self.username = "alice"
        self.company_id = 1
        self.department_id = 2


class _Company:
    name = "Acme"


class _Department:
    name = "R&D"


class _OrgStore:
    def get_company(self, company_id):  # noqa: ARG002
        return _Company()

    def get_department(self, department_id):  # noqa: ARG002
        return _Department()


class TestAuditLogManagerUnit(unittest.TestCase):
    def test_log_ctx_event_and_list_events(self):
        td = make_temp_dir(prefix="ragflowauth_audit_mgr")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            store = AuditLogStore(db_path=db_path)
            mgr = AuditLogManager(store=store)

            ctx = SimpleNamespace(
                payload=SimpleNamespace(sub="u1"),
                user=_User(),
                deps=SimpleNamespace(org_directory_store=_OrgStore(), org_structure_manager=_OrgStore()),
            )
            mgr.log_record_change(
                ctx=ctx,
                action="paper_session_delete",
                source="paper_download",
                resource_type="paper_session",
                resource_id="s1",
                event_type="delete",
                before={"exists": True},
                after={"exists": False},
                reason="cleanup",
                request_id="rid-1",
                client_ip="127.0.0.1",
                meta={"session_id": "s1"},
            )
            data = mgr.list_events(action="paper_session_delete", limit=10)

            self.assertEqual(data["total"], 1)
            item = data["items"][0]
            self.assertEqual(item["action"], "paper_session_delete")
            self.assertEqual(item["username"], "alice")
            self.assertEqual(item["resource_type"], "paper_session")
            self.assertEqual(item["resource_id"], "s1")
            self.assertEqual(item["request_id"], "rid-1")
            self.assertEqual(item["before"], {"exists": True})
            self.assertEqual(item["after"], {"exists": False})
            self.assertEqual(item["meta"], {"session_id": "s1"})
            self.assertIsNotNone(item["event_hash"])
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
