import os
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.database.sqlite import connect_sqlite
from backend.services.notification import NotificationService, NotificationServiceError, NotificationStore
from backend.services.org_directory.manager import OrgStructureManager
from backend.services.org_directory.store import OrgDirectoryStore
from backend.services.users.store import UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _NoopEmailAdapter:
    def send(self, **kwargs):  # noqa: ARG002
        return None


class _StubDingTalkAdapter:
    def __init__(self, *, validation_error: str | None = None):
        self.validation_error = validation_error
        self.validate_calls: list[dict] = []

    def validate_channel(self, *, channel: dict):
        self.validate_calls.append(channel)
        if self.validation_error:
            raise RuntimeError(self.validation_error)
        return "access-token"

    def send(self, **kwargs):  # noqa: ARG002
        return None


def _insert_company(db_path: str, *, company_id: int, name: str) -> None:
    conn = connect_sqlite(db_path)
    try:
        conn.execute(
            """
            INSERT INTO companies (company_id, name, source_key, created_at_ms, updated_at_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (company_id, name, f"company:{company_id}", 1, 1),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_department(
    db_path: str,
    *,
    department_id: int,
    name: str,
    company_id: int,
    parent_department_id: int | None = None,
    level_no: int = 1,
    path_name: str | None = None,
) -> None:
    conn = connect_sqlite(db_path)
    try:
        conn.execute(
            """
            INSERT INTO departments (
                department_id,
                name,
                company_id,
                parent_department_id,
                source_key,
                source_department_id,
                level_no,
                path_name,
                sort_order,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                department_id,
                name,
                company_id,
                parent_department_id,
                f"department:{department_id}",
                str(department_id),
                level_no,
                path_name or name,
                0,
                1,
                1,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_employee(
    db_path: str,
    *,
    employee_user_id: str,
    name: str,
    company_id: int,
    department_id: int | None,
    source_key: str,
) -> None:
    conn = connect_sqlite(db_path)
    try:
        conn.execute(
            """
            INSERT INTO org_employees (
                employee_user_id,
                name,
                email,
                employee_no,
                department_manager_name,
                is_department_manager,
                company_id,
                department_id,
                source_key,
                sort_order,
                created_at_ms,
                updated_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee_user_id,
                name,
                None,
                None,
                None,
                0,
                company_id,
                department_id,
                source_key,
                0,
                1,
                1,
            ),
        )
        conn.commit()
    finally:
        conn.close()


class TestNotificationRecipientMapRebuildUnit(unittest.TestCase):
    def test_rebuild_success_writes_org_user_directory_and_clears_aliases(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_success")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            dingtalk = _StubDingTalkAdapter()
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=dingtalk,
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )

            _insert_company(db_path, company_id=1, name="Acme")
            _insert_company(db_path, company_id=2, name="Beta")
            _insert_department(db_path, department_id=10, name="QA", company_id=1, path_name="Acme / QA")
            _insert_department(db_path, department_id=20, name="研发", company_id=1, path_name="Acme / 研发")
            _insert_department(db_path, department_id=30, name="QA", company_id=2, path_name="Beta / QA")

            _insert_employee(
                db_path,
                employee_user_id="ding-alice",
                name="Alice",
                company_id=1,
                department_id=10,
                source_key="employee:alice",
            )
            _insert_employee(
                db_path,
                employee_user_id="ding-bob",
                name="Bob",
                company_id=1,
                department_id=10,
                source_key="employee:bob",
            )
            _insert_employee(
                db_path,
                employee_user_id="ding-carol",
                name="Carol",
                company_id=1,
                department_id=20,
                source_key="employee:carol",
            )
            alice = user_store.create_user(
                username="alice",
                password="pw",
                full_name="Alice",
                company_id=1,
                department_id=10,
                status="active",
            )
            bob = user_store.create_user(
                username="bob",
                password="pw",
                full_name="Bob",
                company_id=1,
                department_id=10,
                status="active",
            )

            summary = service.rebuild_dingtalk_recipient_map_from_org(
                channel_id="ding-main",
                user_store=user_store,
                org_directory_store=org_manager,
            )

            self.assertEqual(summary["channel_id"], "ding-main")
            self.assertEqual(summary["org_user_count"], 3)
            self.assertEqual(summary["directory_entry_count"], 3)
            self.assertEqual(summary["alias_entry_count"], 0)
            self.assertEqual(summary["invalid_org_user_count"], 0)
            self.assertEqual(summary["invalid_org_users"], [])
            self.assertEqual(len(dingtalk.validate_calls), 1)

            channel = store.get_channel("ding-main")
            self.assertIsNotNone(channel)
            self.assertEqual(
                channel["config"]["recipient_map"],
                {},
            )
            self.assertEqual(
                channel["config"]["recipient_directory"],
                {
                    "ding-alice": {"full_name": "Alice", "company_id": 1, "department_id": 10},
                    "ding-bob": {"full_name": "Bob", "company_id": 1, "department_id": 10},
                    "ding-carol": {"full_name": "Carol", "company_id": 1, "department_id": 20},
                },
            )
            self.assertNotIn("Alice", channel["config"]["recipient_map"])
            self.assertNotIn("Alice", channel["config"]["recipient_directory"])
            self.assertEqual(user_store.get_by_user_id(alice.user_id).employee_user_id, "ding-alice")
            self.assertEqual(user_store.get_by_user_id(bob.user_id).employee_user_id, "ding-bob")
        finally:
            cleanup_dir(td)

    def test_rebuild_syncs_employee_user_ids_with_company_and_department_narrowing(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_user_binding")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=_StubDingTalkAdapter(),
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )

            _insert_company(db_path, company_id=1, name="Acme")
            _insert_company(db_path, company_id=2, name="Beta")
            _insert_department(db_path, department_id=10, name="QA", company_id=1, path_name="Acme / QA")
            _insert_department(db_path, department_id=20, name="RD", company_id=1, path_name="Acme / RD")
            _insert_department(db_path, department_id=30, name="QA", company_id=2, path_name="Beta / QA")
            _insert_employee(
                db_path,
                employee_user_id="ding-same-qa",
                name="Same Name",
                company_id=1,
                department_id=10,
                source_key="employee:same:qa",
            )
            _insert_employee(
                db_path,
                employee_user_id="ding-same-rd",
                name="Same Name",
                company_id=1,
                department_id=20,
                source_key="employee:same:rd",
            )
            _insert_employee(
                db_path,
                employee_user_id="ding-same-beta",
                name="Same Name",
                company_id=2,
                department_id=30,
                source_key="employee:same:beta",
            )

            qa_user = user_store.create_user(
                username="same_qa",
                password="pw",
                full_name="Same Name",
                company_id=1,
                department_id=10,
                status="active",
            )
            beta_user = user_store.create_user(
                username="same_beta",
                password="pw",
                full_name="Same Name",
                company_id=2,
                department_id=30,
                status="active",
            )
            ambiguous_user = user_store.create_user(
                username="same_ambiguous",
                password="pw",
                full_name="Same Name",
                status="active",
            )

            service.rebuild_dingtalk_recipient_map_from_org(
                channel_id="ding-main",
                user_store=user_store,
                org_directory_store=org_manager,
            )

            self.assertEqual(user_store.get_by_user_id(qa_user.user_id).employee_user_id, "ding-same-qa")
            self.assertEqual(user_store.get_by_user_id(beta_user.user_id).employee_user_id, "ding-same-beta")
            self.assertIsNone(user_store.get_by_user_id(ambiguous_user.user_id).employee_user_id)
        finally:
            cleanup_dir(td)

    def test_rebuild_fails_when_org_employee_user_id_missing(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_missing_org_user_id")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=_StubDingTalkAdapter(),
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )

            _insert_company(db_path, company_id=1, name="Acme")
            _insert_department(db_path, department_id=10, name="QA", company_id=1, path_name="Acme / QA")
            _insert_employee(
                db_path,
                employee_user_id="",
                name="Alice",
                company_id=1,
                department_id=10,
                source_key="employee:alice",
            )

            with self.assertRaises(NotificationServiceError) as ctx:
                service.rebuild_dingtalk_recipient_map_from_org(
                    channel_id="ding-main",
                    user_store=user_store,
                    org_directory_store=org_manager,
                )
            self.assertEqual(str(ctx.exception), "notification_dingtalk_org_directory_invalid")

            channel = store.get_channel("ding-main")
            self.assertIsNotNone(channel)
            self.assertEqual(channel["config"]["recipient_map"], {"legacy": "legacy-user"})
            self.assertNotIn("recipient_directory", channel["config"])
        finally:
            cleanup_dir(td)

    def test_rebuild_fails_when_org_employee_user_id_duplicate(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_duplicate_org_user_id")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=_StubDingTalkAdapter(),
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )

            _insert_company(db_path, company_id=1, name="Acme")
            _insert_department(db_path, department_id=10, name="QA", company_id=1, path_name="Acme / QA")
            _insert_employee(
                db_path,
                employee_user_id="ding-alice",
                name="Alice",
                company_id=1,
                department_id=10,
                source_key="employee:alice",
            )
            _insert_employee(
                db_path,
                employee_user_id="ding-alice",
                name="Alice 2",
                company_id=1,
                department_id=10,
                source_key="employee:alice:dup",
            )

            with self.assertRaises(NotificationServiceError) as ctx:
                service.rebuild_dingtalk_recipient_map_from_org(
                    channel_id="ding-main",
                    user_store=user_store,
                    org_directory_store=org_manager,
                )
            self.assertEqual(str(ctx.exception), "notification_dingtalk_org_directory_invalid")

            channel = store.get_channel("ding-main")
            self.assertIsNotNone(channel)
            self.assertEqual(channel["config"]["recipient_map"], {"legacy": "legacy-user"})
            self.assertNotIn("recipient_directory", channel["config"])
        finally:
            cleanup_dir(td)

    def test_rebuild_token_validation_failure_leaves_channel_config_unchanged(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_token_fail")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=_StubDingTalkAdapter(
                    validation_error="dingtalk_access_token_failed:http_400:invalidClientIdOrSecret"
                ),
            )
            service.upsert_channel(
                channel_id="ding-main",
                channel_type="dingtalk",
                name="Main DingTalk",
                enabled=True,
                config={
                    "app_key": "real-key",
                    "app_secret": "real-secret",
                    "agent_id": "4432005762",
                    "recipient_map": {"legacy": "legacy-user"},
                },
            )

            _insert_company(db_path, company_id=1, name="Acme")
            _insert_department(db_path, department_id=10, name="QA", company_id=1, path_name="Acme / QA")
            _insert_employee(
                db_path,
                employee_user_id="ding-alice",
                name="Alice",
                company_id=1,
                department_id=10,
                source_key="employee:alice",
            )
            user_store.create_user(
                username="alice",
                password="pw",
                full_name="Alice",
                company_id=1,
                department_id=10,
                status="active",
            )

            with self.assertRaises(NotificationServiceError) as ctx:
                service.rebuild_dingtalk_recipient_map_from_org(
                    channel_id="ding-main",
                    user_store=user_store,
                    org_directory_store=org_manager,
                )
            self.assertEqual(str(ctx.exception), "dingtalk_access_token_failed:http_400:invalidClientIdOrSecret")

            channel = store.get_channel("ding-main")
            self.assertIsNotNone(channel)
            self.assertEqual(channel["config"]["recipient_map"], {"legacy": "legacy-user"})
        finally:
            cleanup_dir(td)

    def test_rebuild_rejects_non_dingtalk_channel(self):
        td = make_temp_dir(prefix="ragflowauth_notification_recipient_map_wrong_channel")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)

            user_store = UserStore(db_path=db_path)
            org_manager = OrgStructureManager(store=OrgDirectoryStore(db_path=db_path))
            store = NotificationStore(db_path=db_path)
            service = NotificationService(
                store=store,
                email_adapter=_NoopEmailAdapter(),
                dingtalk_adapter=_StubDingTalkAdapter(),
            )
            service.upsert_channel(
                channel_id="email-main",
                channel_type="email",
                name="Main Email",
                enabled=True,
                config={"host": "smtp.example.com"},
            )

            with self.assertRaises(NotificationServiceError) as ctx:
                service.rebuild_dingtalk_recipient_map_from_org(
                    channel_id="email-main",
                    user_store=user_store,
                    org_directory_store=org_manager,
                )
            self.assertEqual(str(ctx.exception), "notification_channel_not_dingtalk")
        finally:
            cleanup_dir(td)
