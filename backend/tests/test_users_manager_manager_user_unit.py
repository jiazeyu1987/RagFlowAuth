import unittest
from types import SimpleNamespace

from backend.models.user import UserCreate, UserUpdate
from backend.services.users.manager import UserManagementError, UserManagementManager


def _make_user(
    user_id: str,
    *,
    username: str,
    employee_user_id: str | None = None,
    role: str = "viewer",
    company_id: int = 1,
    department_id: int = 10,
    status: str = "active",
    manager_user_id: str | None = None,
):
    return SimpleNamespace(
        user_id=user_id,
        username=username,
        employee_user_id=employee_user_id,
        full_name=username.title(),
        email=f"{username}@example.com",
        manager_user_id=manager_user_id,
        role=role,
        group_id=1,
        group_ids=[1],
        company_id=company_id,
        department_id=department_id,
        status=status,
        can_change_password=True,
        disable_login_enabled=False,
        disable_login_until_ms=None,
        max_login_sessions=3,
        idle_timeout_minutes=120,
        created_at_ms=1,
        last_login_at_ms=None,
        managed_kb_root_node_id=None,
        tool_ids=[],
    )


class _FakePort:
    def __init__(self):
        self.users = {
            "admin-1": _make_user("admin-1", username="admin", role="admin"),
            "mgr-1": _make_user("mgr-1", username="manager_one", role="sub_admin"),
            "mgr-2": _make_user("mgr-2", username="manager_two", role="sub_admin", company_id=2),
            "mgr-inactive": _make_user("mgr-inactive", username="manager_inactive", role="sub_admin", status="inactive"),
            "mgr-viewer": _make_user("mgr-viewer", username="manager_viewer", role="viewer"),
            "user-1": _make_user("user-1", username="user_one", employee_user_id="bound_employee"),
        }
        self.employee_profiles = {
            "new_user": SimpleNamespace(name="New User", company_id=1, department_id=10),
            "new_user_without_department": SimpleNamespace(name="No Department User", company_id=1, department_id=None),
            "new_user_without_department_and_default": SimpleNamespace(
                name="No Department Without Default",
                company_id=9,
                department_id=None,
            ),
            "bound_employee": SimpleNamespace(name="Bound Employee", company_id=1, department_id=10),
            "user_manager_user_not_found": SimpleNamespace(name="Not Found Manager", company_id=1, department_id=10),
            "user_manager_user_inactive": SimpleNamespace(name="Inactive Manager", company_id=1, department_id=10),
            "user_manager_user_company_mismatch": SimpleNamespace(name="Cross Company Manager", company_id=1, department_id=10),
            "user_manager_user_must_be_sub_admin": SimpleNamespace(name="Viewer Manager", company_id=1, department_id=10),
            "viewer_without_manager": SimpleNamespace(name="Viewer Without Manager", company_id=1, department_id=10),
            "sub_admin_new": SimpleNamespace(name="Sub Admin New", company_id=1, department_id=10),
            "sub_admin_invalid_root": SimpleNamespace(name="Sub Admin Invalid Root", company_id=1, department_id=10),
            "sub_admin_missing_root": SimpleNamespace(name="Sub Admin Missing Root", company_id=1, department_id=10),
            "sub_admin_tools": SimpleNamespace(name="Sub Admin Tools", company_id=1, department_id=10),
            "cross_company_user": SimpleNamespace(name="Cross Company User", company_id=1, department_id=20),
        }
        self.create_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.tool_permission_calls: list[dict] = []
        self.tool_permission_sync_calls: list[dict] = []
        self.managed_roots = {
            (1, "node-1"): "/Root 1",
            (2, "node-2"): "/Root 2",
        }
        self.default_departments = {
            1: 10,
            2: 20,
        }

    def list_users(self, **_kwargs):
        return [self.users["user-1"]]

    def get_user(self, user_id: str):
        return self.users.get(str(user_id))

    def create_user(self, **kwargs):
        self.create_calls.append(dict(kwargs))
        user = _make_user(
            "created-1",
            username=str(kwargs["username"]),
            role=str(kwargs.get("role") or "viewer"),
            company_id=int(kwargs["company_id"]) if kwargs.get("company_id") is not None else 1,
            department_id=int(kwargs["department_id"]) if kwargs.get("department_id") is not None else 10,
            manager_user_id=kwargs.get("manager_user_id"),
        )
        user.full_name = kwargs.get("full_name")
        user.email = kwargs.get("email")
        user.employee_user_id = kwargs.get("employee_user_id")
        user.managed_kb_root_node_id = kwargs.get("managed_kb_root_node_id")
        user.tool_ids = []
        self.users[user.user_id] = user
        return user

    def update_user(self, **kwargs):
        self.update_calls.append(dict(kwargs))
        user = self.users.get(str(kwargs["user_id"]))
        if not user:
            return None
        if "manager_user_id" in kwargs:
            value = kwargs.get("manager_user_id")
            user.manager_user_id = str(value).strip() or None if value is not None else user.manager_user_id
        if kwargs.get("company_id") is not None:
            user.company_id = int(kwargs["company_id"])
        if "managed_kb_root_node_id" in kwargs:
            value = kwargs.get("managed_kb_root_node_id")
            user.managed_kb_root_node_id = (
                (str(value).strip() or None) if value is not None else user.managed_kb_root_node_id
            )
        return user

    def delete_user(self, _user_id: str) -> bool:
        return False

    def update_password(self, _user_id: str, _new_password: str) -> None:
        return None

    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None:
        user = self.users[str(user_id)]
        user.group_ids = list(group_ids)
        user.group_id = group_ids[0] if group_ids else None

    def list_user_tool_ids(self, user_id: str) -> list[str]:
        user = self.users[str(user_id)]
        return sorted(
            {
                str(tool_id or "").strip()
                for tool_id in (user.tool_ids or [])
                if str(tool_id or "").strip()
            }
        )

    def set_user_tool_permissions(
        self,
        user_id: str,
        tool_ids: list[str],
        *,
        granted_by_user_id: str | None = None,
    ) -> None:
        user = self.users[str(user_id)]
        user.tool_ids = sorted(
            {
                str(tool_id or "").strip()
                for tool_id in (tool_ids or [])
                if str(tool_id or "").strip()
            }
        )
        self.tool_permission_calls.append(
            {
                "user_id": str(user_id),
                "tool_ids": list(user.tool_ids),
                "granted_by_user_id": granted_by_user_id,
            }
        )

    def set_user_tool_permissions_with_managed_viewer_sync(
        self,
        *,
        sub_admin_user_id: str,
        tool_ids: list[str],
        granted_by_user_id: str | None = None,
    ) -> None:
        self.set_user_tool_permissions(
            sub_admin_user_id,
            tool_ids,
            granted_by_user_id=granted_by_user_id,
        )
        allowed = set(self.list_user_tool_ids(sub_admin_user_id))
        for user in self.users.values():
            if str(getattr(user, "role", "") or "") != "viewer":
                continue
            if str(getattr(user, "manager_user_id", "") or "") != str(sub_admin_user_id):
                continue
            user.tool_ids = sorted(
                set(self.list_user_tool_ids(user.user_id)).intersection(allowed)
            )
        self.tool_permission_sync_calls.append(
            {
                "sub_admin_user_id": str(sub_admin_user_id),
                "tool_ids": sorted(allowed),
                "granted_by_user_id": granted_by_user_id,
            }
        )

    def enforce_login_session_limit(self, _user_id: str, _max_sessions: int) -> list[str]:
        return []

    def get_permission_group(self, group_id: int):
        if group_id == 1:
            return {"group_id": 1, "group_name": "viewer"}
        if group_id == 9:
            return {"group_id": 9, "group_name": "tools-sub-admin"}
        return None

    def get_group_by_name(self, name: str):
        if name == "viewer":
            return {"group_id": 1, "group_name": "viewer"}
        return None

    def get_company(self, company_id: int):
        return SimpleNamespace(name=f"Company-{company_id}") if company_id in {1, 2} else None

    def get_department(self, department_id: int):
        if department_id == 10:
            return SimpleNamespace(name="Department-10", path_name="Company-1 / Department-10", company_id=1)
        if department_id == 20:
            return SimpleNamespace(name="Department-20", path_name="Company-2 / Department-20", company_id=2)
        return None

    def get_employee_by_user_id(self, employee_user_id: str):
        normalized = str(employee_user_id or "").strip()
        profile = self.employee_profiles.get(normalized)
        if not profile:
            return None
        return SimpleNamespace(
            employee_user_id=normalized,
            name=profile.name,
            company_id=profile.company_id,
            department_id=profile.department_id,
        )

    def get_default_department_id_for_company(self, company_id: int):
        try:
            key = int(company_id)
        except Exception:
            return None
        return self.default_departments.get(key)

    def get_user_by_employee_user_id(self, employee_user_id: str):
        normalized = str(employee_user_id or "").strip()
        if not normalized:
            return None
        for user in self.users.values():
            if str(getattr(user, "employee_user_id", "") or "").strip() == normalized:
                return user
        return None

    def get_managed_kb_root_path(self, *, company_id: int | None, node_id: str | None):
        if company_id is None or node_id is None:
            return None
        return self.managed_roots.get((int(company_id), str(node_id)))

    def get_login_session_summary(self, _user_id: str, _idle_timeout_minutes: int | None):
        return {"active_session_count": 0, "active_session_last_activity_at_ms": None}

    def get_login_session_summaries(self, _idle_timeout_by_user: dict[str, int | None]):
        return {"user-1": {"active_session_count": 0, "active_session_last_activity_at_ms": None}}


class UserManagementManagerManagerUserTests(unittest.TestCase):
    def setUp(self):
        self.port = _FakePort()
        self.manager = UserManagementManager(self.port)

    def test_create_user_accepts_valid_manager_user(self):
        response = self.manager.create_user(
                user_data=UserCreate(
                    username="new_user_alias",
                    password="Pass1234",
                    employee_user_id="new_user",
                    full_name="New User",
                    email="new_user@example.com",
                    company_id=1,
                    department_id=10,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )

        self.assertEqual("new_user_alias", self.port.create_calls[0]["username"])
        self.assertEqual("mgr-1", self.port.create_calls[0]["manager_user_id"])
        self.assertEqual("new_user", self.port.create_calls[0]["employee_user_id"])
        self.assertEqual("new_user", response.employee_user_id)
        self.assertEqual("mgr-1", response.manager_user_id)
        self.assertEqual("manager_one", response.manager_username)

    def test_create_user_requires_employee_user_id(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="new_user",
                    password="Pass1234",
                    full_name="New User",
                    company_id=1,
                    department_id=10,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )

        self.assertEqual("employee_user_id_required", ctx.exception.code)

    def test_create_user_rejects_unknown_employee_user_id(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="missing_employee",
                    password="Pass1234",
                    employee_user_id="missing_employee",
                    full_name="Missing Employee",
                    company_id=1,
                    department_id=10,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )

        self.assertEqual("employee_user_id_not_found", ctx.exception.code)

    def test_create_user_allows_username_different_from_employee_user_id(self):
        response = self.manager.create_user(
            user_data=UserCreate(
                username="new_user_alias",
                password="Pass1234",
                employee_user_id="new_user",
                full_name="New User",
                company_id=1,
                department_id=10,
                manager_user_id="mgr-1",
            ),
            created_by="admin-1",
        )
        self.assertEqual("new_user_alias", self.port.create_calls[-1]["username"])
        self.assertEqual("new_user", response.employee_user_id)

    def test_create_user_rejects_employee_user_id_already_bound(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="another_alias",
                    password="Pass1234",
                    employee_user_id="bound_employee",
                    full_name="Bound Employee",
                    company_id=1,
                    department_id=10,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )
        self.assertEqual("employee_user_id_already_bound", ctx.exception.code)

    def test_create_user_rejects_org_profile_mismatch(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="new_user",
                    password="Pass1234",
                    employee_user_id="new_user",
                    full_name="Wrong Name",
                    company_id=1,
                    department_id=10,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )

        self.assertEqual("employee_org_profile_mismatch", ctx.exception.code)

    def test_create_user_uses_default_department_when_employee_profile_missing_department(self):
        response = self.manager.create_user(
            user_data=UserCreate(
                username="new_user_alias",
                password="Pass1234",
                employee_user_id="new_user_without_department",
                full_name="No Department User",
                company_id=1,
                department_id=10,
                manager_user_id="mgr-1",
            ),
            created_by="admin-1",
        )

        self.assertEqual(10, self.port.create_calls[-1]["department_id"])
        self.assertEqual(10, response.department_id)

    def test_create_user_rejects_when_default_department_missing_for_employee_company(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="new_user_alias",
                    password="Pass1234",
                    employee_user_id="new_user_without_department_and_default",
                    full_name="No Department Without Default",
                    company_id=9,
                    department_id=901,
                    manager_user_id="mgr-1",
                ),
                created_by="admin-1",
            )

        self.assertEqual("default_department_not_found_for_company", ctx.exception.code)

    def test_create_user_rejects_missing_or_inactive_or_cross_company_manager(self):
        cases = [
            ("manager_user_not_found", "missing-user"),
            ("manager_user_inactive", "mgr-inactive"),
            ("manager_user_company_mismatch", "mgr-2"),
            ("manager_user_must_be_sub_admin", "mgr-viewer"),
        ]

        for expected_code, manager_user_id in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(UserManagementError) as ctx:
                    self.manager.create_user(
                        user_data=UserCreate(
                            username=f"user_{expected_code}",
                            password="Pass1234",
                            employee_user_id=f"user_{expected_code}",
                            full_name=self.port.employee_profiles[f"user_{expected_code}"].name,
                            company_id=1,
                            department_id=10,
                            manager_user_id=manager_user_id,
                        ),
                        created_by="admin-1",
                    )
                self.assertEqual(expected_code, ctx.exception.code)

    def test_create_viewer_requires_manager_user(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="viewer_without_manager",
                    password="Pass1234",
                    employee_user_id="viewer_without_manager",
                    full_name="Viewer Without Manager",
                    company_id=1,
                    department_id=10,
                ),
                created_by="admin-1",
            )
        self.assertEqual("manager_user_required_for_viewer", ctx.exception.code)

    def test_create_sub_admin_clears_manager_user(self):
        response = self.manager.create_user(
            user_data=UserCreate(
                username="sub_admin_new",
                password="Pass1234",
                employee_user_id="sub_admin_new",
                full_name="Sub Admin New",
                company_id=1,
                department_id=10,
                role="sub_admin",
                manager_user_id="mgr-1",
                managed_kb_root_node_id="node-1",
            ),
            created_by="admin-1",
        )

        self.assertIsNone(self.port.create_calls[-1]["manager_user_id"])
        self.assertIsNone(response.manager_user_id)
        self.assertEqual("node-1", self.port.create_calls[-1]["managed_kb_root_node_id"])
        self.assertEqual("/Root 1", response.managed_kb_root_path)

    def test_create_sub_admin_requires_existing_root_in_target_company(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="sub_admin_invalid_root",
                    password="Pass1234",
                    employee_user_id="sub_admin_invalid_root",
                    full_name="Sub Admin Invalid Root",
                    company_id=1,
                    department_id=10,
                    role="sub_admin",
                    managed_kb_root_node_id="missing-node",
                ),
                created_by="admin-1",
            )

        self.assertEqual("managed_kb_root_node_not_found", ctx.exception.code)

    def test_create_sub_admin_requires_root(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="sub_admin_missing_root",
                    password="Pass1234",
                    employee_user_id="sub_admin_missing_root",
                    full_name="Sub Admin Missing Root",
                    company_id=1,
                    department_id=10,
                    role="sub_admin",
                ),
                created_by="admin-1",
            )

        self.assertEqual("managed_kb_root_node_required_for_sub_admin", ctx.exception.code)

    def test_create_sub_admin_keeps_permission_groups(self):
        response = self.manager.create_user(
            user_data=UserCreate(
                username="sub_admin_tools",
                password="Pass1234",
                employee_user_id="sub_admin_tools",
                full_name="Sub Admin Tools",
                company_id=1,
                department_id=10,
                role="sub_admin",
                group_ids=[9],
                managed_kb_root_node_id="node-1",
            ),
            created_by="admin-1",
        )

        self.assertEqual([9], self.port.users[response.user_id].group_ids)
        self.assertEqual(9, self.port.users[response.user_id].group_id)

    def test_update_user_rejects_self_reference_manager(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(
                user_id="user-1",
                user_data=UserUpdate(manager_user_id="user-1"),
            )
        self.assertEqual("manager_user_self_reference_not_allowed", ctx.exception.code)

    def test_update_sub_admin_requires_root_in_target_company(self):
        self.port.users["user-1"].role = "sub_admin"
        self.port.users["user-1"].company_id = 1
        self.port.users["user-1"].department_id = 10
        self.port.users["user-1"].managed_kb_root_node_id = "node-1"

        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(
                user_id="user-1",
                user_data=UserUpdate(company_id=2, department_id=20, managed_kb_root_node_id="node-1"),
            )

        self.assertEqual("managed_kb_root_node_not_found", ctx.exception.code)

    def test_update_non_sub_admin_clears_managed_root(self):
        self.port.users["user-1"].managed_kb_root_node_id = "node-1"
        self.port.users["user-1"].manager_user_id = "mgr-1"

        self.manager.update_user(
            user_id="user-1",
            user_data=UserUpdate(full_name="Viewer User"),
        )

        self.assertEqual("", self.port.update_calls[-1]["managed_kb_root_node_id"])

    def test_update_sub_admin_keeps_permission_groups(self):
        self.port.users["user-1"].role = "sub_admin"
        self.port.users["user-1"].company_id = 1
        self.port.users["user-1"].department_id = 10
        self.port.users["user-1"].managed_kb_root_node_id = "node-1"

        response = self.manager.update_user(
            user_id="user-1",
            user_data=UserUpdate(group_ids=[9]),
        )

        self.assertEqual([9], response.group_ids)
        self.assertEqual(9, self.port.users["user-1"].group_id)

    def test_update_admin_cannot_assign_viewer_tool_ids_directly(self):
        self.port.users["user-1"].manager_user_id = "mgr-1"
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.update_user(
                user_id="user-1",
                user_data=UserUpdate(tool_ids=["nmpa"]),
                updated_by="admin-1",
            )

        self.assertEqual("admin_can_only_assign_sub_admin_tools", ctx.exception.code)
        self.assertEqual(403, ctx.exception.status_code)

    def test_update_admin_can_assign_sub_admin_tool_ids(self):
        self.port.users["user-1"].role = "sub_admin"
        self.port.users["user-1"].managed_kb_root_node_id = "node-1"

        response = self.manager.update_user(
            user_id="user-1",
            user_data=UserUpdate(tool_ids=["nmpa"]),
            updated_by="admin-1",
        )

        self.assertEqual(["nmpa"], response.tool_ids)
        self.assertEqual(
            {
                "sub_admin_user_id": "user-1",
                "tool_ids": ["nmpa"],
                "granted_by_user_id": "admin-1",
            },
            self.port.tool_permission_sync_calls[-1],
        )

    def test_create_user_rejects_department_from_other_company(self):
        with self.assertRaises(UserManagementError) as ctx:
            self.manager.create_user(
                user_data=UserCreate(
                    username="cross_company_user",
                    password="Pass1234",
                    employee_user_id="cross_company_user",
                    full_name="Cross Company User",
                    company_id=1,
                    department_id=20,
                    group_ids=[1],
                ),
                created_by="admin-1",
            )
        self.assertEqual("department_company_mismatch", ctx.exception.code)

    def test_get_user_and_list_users_include_manager_fields(self):
        self.port.users["user-1"].manager_user_id = "mgr-1"
        self.port.users["mgr-1"].managed_kb_root_node_id = "node-1"

        detail = self.manager.get_user("user-1")
        listing = self.manager.list_users(
            q=None,
            role=None,
            group_id=None,
            company_id=None,
            department_id=None,
            status=None,
            created_from_ms=None,
            created_to_ms=None,
            limit=20,
        )

        self.assertEqual("mgr-1", detail.manager_user_id)
        self.assertEqual("manager_one", detail.manager_username)
        self.assertEqual("mgr-1", listing[0].manager_user_id)
        self.assertEqual("manager_one", listing[0].manager_username)

        sub_admin_detail = self.manager.get_user("mgr-1")
        self.assertEqual("/Root 1", sub_admin_detail.managed_kb_root_path)


if __name__ == "__main__":
    unittest.main()
