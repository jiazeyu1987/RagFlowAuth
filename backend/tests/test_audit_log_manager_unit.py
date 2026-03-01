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


class _UserStore:
    def get_by_user_id(self, user_id):  # noqa: ARG002
        return _User()


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
                deps=SimpleNamespace(user_store=_UserStore(), org_directory_store=_OrgStore()),
            )
            mgr.log_ctx_event(ctx=ctx, action="paper_session_delete", source="paper_download", meta={"session_id": "s1"})
            data = mgr.list_events(action="paper_session_delete", limit=10)

            self.assertEqual(data["total"], 1)
            self.assertEqual(data["items"][0]["action"], "paper_session_delete")
            self.assertEqual(data["items"][0]["username"], "alice")
        finally:
            cleanup_dir(td)


if __name__ == "__main__":
    unittest.main()
