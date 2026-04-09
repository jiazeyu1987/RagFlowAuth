import unittest
from types import SimpleNamespace

from backend.app.modules.users.repo import UsersRepo


class _AuthSessionStore:
    def __init__(self):
        self.calls = []

    def enforce_user_session_limit(self, **kwargs):
        self.calls.append(("enforce_user_session_limit", kwargs))
        return ["s-1"]

    def get_active_session_summary(self, **kwargs):
        self.calls.append(("get_active_session_summary", kwargs))
        return {
            "active_session_count": 2,
            "active_session_last_activity_at_ms": 1234,
        }

    def get_active_session_summaries(self, **kwargs):
        self.calls.append(("get_active_session_summaries", kwargs))
        return {"u-1": {"active_session_count": 1, "active_session_last_activity_at_ms": 5678}}


class _PermissionGroupStore:
    def __init__(self, prefix="deps"):
        self.prefix = prefix
        self.calls = []

    def get_group(self, group_id):
        self.calls.append(("get_group", group_id))
        return {"group_id": group_id, "source": self.prefix}

    def get_group_by_name(self, name):
        self.calls.append(("get_group_by_name", name))
        return {"group_name": name, "source": self.prefix}


class _UserStore:
    def __init__(self):
        self.calls = []

    def list_users(self, **kwargs):
        self.calls.append(("list_users", kwargs))
        return ["user-a"]

    def get_by_user_id(self, user_id):
        self.calls.append(("get_by_user_id", user_id))
        return {"user_id": user_id}

    def get_by_employee_user_id(self, employee_user_id):
        self.calls.append(("get_by_employee_user_id", employee_user_id))
        return {"employee_user_id": employee_user_id}

    def create_user(self, **kwargs):
        self.calls.append(("create_user", kwargs))
        return {"user_id": "u-created"}

    def update_user(self, **kwargs):
        self.calls.append(("update_user", kwargs))
        return {"user_id": kwargs.get("user_id")}

    def delete_user(self, user_id):
        self.calls.append(("delete_user", user_id))
        return 1

    def update_password(self, user_id, new_password):
        self.calls.append(("update_password", {"user_id": user_id, "new_password": new_password}))

    def set_user_permission_groups(self, user_id, group_ids):
        self.calls.append(("set_user_permission_groups", {"user_id": user_id, "group_ids": group_ids}))


class _OrgStructureManager:
    def __init__(self):
        self.calls = []

    def get_company(self, company_id):
        self.calls.append(("get_company", company_id))
        return {"company_id": company_id}

    def get_department(self, department_id):
        self.calls.append(("get_department", department_id))
        return {"department_id": department_id}

    def get_employee_by_user_id(self, employee_user_id):
        self.calls.append(("get_employee_by_user_id", employee_user_id))
        return {"employee_user_id": employee_user_id}

    def list_departments_flat(self):
        self.calls.append(("list_departments_flat", None))
        return [
            SimpleNamespace(department_id=11, company_id=1),
            SimpleNamespace(department_id=12, company_id=1),
            {"id": 21, "company_id": 2},
        ]


def _build_repo(
    *,
    auth_session_store=None,
    deps_permission_group_store=None,
    explicit_permission_group_store=None,
    user_store=None,
    org_structure_manager=None,
):
    deps = SimpleNamespace(
        user_store=user_store or SimpleNamespace(),
        auth_session_store=auth_session_store,
        permission_group_store=deps_permission_group_store,
        org_structure_manager=org_structure_manager or SimpleNamespace(),
    )
    return UsersRepo(deps, permission_group_store=explicit_permission_group_store)


class UsersRepoUnitTest(unittest.TestCase):
    def test_login_session_helpers_return_empty_results_without_store(self):
        repo = _build_repo()

        self.assertEqual(repo.enforce_login_session_limit("u-1", 3), [])
        self.assertEqual(
            repo.get_login_session_summary("u-1", 120),
            {
                "active_session_count": 0,
                "active_session_last_activity_at_ms": None,
            },
        )
        self.assertEqual(repo.get_login_session_summaries({"u-1": 120}), {})

    def test_login_session_helpers_delegate_to_auth_session_store(self):
        store = _AuthSessionStore()
        repo = _build_repo(auth_session_store=store)

        self.assertEqual(repo.enforce_login_session_limit("u-1", 3), ["s-1"])
        self.assertEqual(
            repo.get_login_session_summary("u-1", 120),
            {
                "active_session_count": 2,
                "active_session_last_activity_at_ms": 1234,
            },
        )
        self.assertEqual(
            repo.get_login_session_summaries({"u-1": 120}),
            {"u-1": {"active_session_count": 1, "active_session_last_activity_at_ms": 5678}},
        )
        self.assertEqual(
            store.calls,
            [
                (
                    "enforce_user_session_limit",
                    {
                        "user_id": "u-1",
                        "max_sessions": 3,
                        "reserve_slots": 0,
                        "reason": "policy_limit_updated",
                    },
                ),
                (
                    "get_active_session_summary",
                    {
                        "user_id": "u-1",
                        "idle_timeout_minutes": 120,
                    },
                ),
                (
                    "get_active_session_summaries",
                    {
                        "idle_timeout_by_user": {"u-1": 120},
                    },
                ),
            ],
        )

    def test_permission_group_helpers_return_none_without_store(self):
        repo = _build_repo()

        self.assertIsNone(repo.get_permission_group(7))
        self.assertIsNone(repo.get_group_by_name("Default"))

    def test_permission_group_helpers_use_explicit_store_before_deps_store(self):
        explicit_store = _PermissionGroupStore(prefix="explicit")
        deps_store = _PermissionGroupStore(prefix="deps")
        repo = _build_repo(
            deps_permission_group_store=deps_store,
            explicit_permission_group_store=explicit_store,
        )

        self.assertEqual(repo.get_permission_group(7), {"group_id": 7, "source": "explicit"})
        self.assertEqual(repo.get_group_by_name("Default"), {"group_name": "Default", "source": "explicit"})
        self.assertEqual(explicit_store.calls, [("get_group", 7), ("get_group_by_name", "Default")])
        self.assertEqual(deps_store.calls, [])

    def test_user_store_helpers_delegate_through_common_user_store_caller(self):
        user_store = _UserStore()
        repo = _build_repo(user_store=user_store)
        create_payload = {
            "username": "alice",
            "password": "Secret123",
            "employee_user_id": "alice",
            "full_name": "Alice",
            "email": "alice@example.com",
            "manager_user_id": "u-sub",
            "company_id": 1,
            "department_id": 11,
            "role": "viewer",
            "group_id": None,
            "status": "active",
            "max_login_sessions": 3,
            "idle_timeout_minutes": 120,
            "can_change_password": True,
            "disable_login_enabled": False,
            "disable_login_until_ms": None,
            "electronic_signature_enabled": True,
            "created_by": "u-admin",
            "managed_kb_root_node_id": None,
        }
        update_payload = {
            "user_id": "u-2",
            "full_name": "Alice",
            "email": "alice@example.com",
            "manager_user_id": "u-sub",
            "company_id": 1,
            "department_id": 11,
            "role": "viewer",
            "group_id": None,
            "status": "active",
            "max_login_sessions": 5,
            "idle_timeout_minutes": 240,
            "can_change_password": False,
            "disable_login_enabled": True,
            "disable_login_until_ms": 987654321,
            "electronic_signature_enabled": False,
            "managed_kb_root_node_id": "node-1",
        }

        self.assertEqual(
            repo.list_users(
                q="alice",
                role="viewer",
                status="active",
                group_id=7,
                company_id=1,
                department_id=11,
                created_from_ms=1000,
                created_to_ms=2000,
                manager_user_id="u-sub",
                limit=50,
            ),
            ["user-a"],
        )
        self.assertEqual(repo.get_user("u-1"), {"user_id": "u-1"})
        self.assertEqual(repo.get_user_by_employee_user_id("alice_emp"), {"employee_user_id": "alice_emp"})
        self.assertEqual(repo.create_user(**create_payload), {"user_id": "u-created"})
        self.assertEqual(repo.update_user(**update_payload), {"user_id": "u-2"})
        self.assertTrue(repo.delete_user("u-3"))
        repo.update_password("u-4", "Secret123")
        repo.set_user_permission_groups("u-5", [7, 9])

        self.assertEqual(
            user_store.calls,
            [
                (
                    "list_users",
                    {
                        "q": "alice",
                        "role": "viewer",
                        "group_id": 7,
                        "company_id": 1,
                        "department_id": 11,
                        "status": "active",
                        "created_from_ms": 1000,
                        "created_to_ms": 2000,
                        "manager_user_id": "u-sub",
                        "limit": 50,
                    },
                ),
                ("get_by_user_id", "u-1"),
                ("get_by_employee_user_id", "alice_emp"),
                ("create_user", create_payload),
                ("update_user", update_payload),
                ("delete_user", "u-3"),
                ("update_password", {"user_id": "u-4", "new_password": "Secret123"}),
                ("set_user_permission_groups", {"user_id": "u-5", "group_ids": [7, 9]}),
            ],
        )

    def test_org_structure_helpers_delegate_through_common_manager_caller(self):
        org_structure_manager = _OrgStructureManager()
        repo = _build_repo(org_structure_manager=org_structure_manager)

        self.assertEqual(repo.get_company(1), {"company_id": 1})
        self.assertEqual(repo.get_department(11), {"department_id": 11})
        self.assertEqual(repo.get_employee_by_user_id("alice"), {"employee_user_id": "alice"})
        self.assertEqual(repo.get_default_department_id_for_company(1), 11)
        self.assertEqual(repo.get_default_department_id_for_company(2), 21)
        self.assertIsNone(repo.get_default_department_id_for_company(3))
        self.assertEqual(
            org_structure_manager.calls,
            [
                ("get_company", 1),
                ("get_department", 11),
                ("get_employee_by_user_id", "alice"),
                ("list_departments_flat", None),
                ("list_departments_flat", None),
                ("list_departments_flat", None),
            ],
        )


if __name__ == "__main__":
    unittest.main()
