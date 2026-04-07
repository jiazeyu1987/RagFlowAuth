from __future__ import annotations

from typing import Any, Optional

from backend.app.dependencies import AppDependencies
from backend.database.schema.ensure import ensure_schema
from backend.database.tenant_paths import resolve_tenant_auth_db_path
from backend.app.modules.users.list_params import build_list_users_kwargs
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeManager


class UsersRepo:
    def __init__(self, deps: AppDependencies, *, permission_group_store=None):
        self._deps = deps
        self._permission_group_store = permission_group_store or getattr(deps, "permission_group_store", None)

    @staticmethod
    def _call_optional_dependency(target, method_name: str, /, *args, default_factory=None, **kwargs):
        if target is None:
            if default_factory is None:
                return None
            return default_factory()
        return getattr(target, method_name)(*args, **kwargs)

    def _call_user_store(self, method_name: str, /, *args, **kwargs):
        return getattr(self._deps.user_store, method_name)(*args, **kwargs)

    def _call_org_structure_manager(self, method_name: str, /, *args, **kwargs):
        return getattr(self._deps.org_structure_manager, method_name)(*args, **kwargs)

    def _call_auth_session_store(self, method_name: str, *, default_factory=None, **kwargs):
        return self._call_optional_dependency(
            getattr(self._deps, "auth_session_store", None),
            method_name,
            default_factory=default_factory,
            **kwargs,
        )

    @staticmethod
    def _empty_login_session_summary() -> dict[str, int | None]:
        return {
            "active_session_count": 0,
            "active_session_last_activity_at_ms": None,
        }

    def _call_permission_group_store(self, method_name: str, /, *args, default_factory=None, **kwargs):
        return self._call_optional_dependency(
            self._permission_group_store,
            method_name,
            *args,
            default_factory=default_factory,
            **kwargs,
        )

    def _build_tenant_knowledge_directory_store(self, *, company_id: int):
        tenant_db_path = resolve_tenant_auth_db_path(
            company_id=company_id,
            base_db_path=getattr(self._deps.user_store, "db_path", None),
        )
        ensure_schema(str(tenant_db_path))
        return KnowledgeDirectoryStore(db_path=str(tenant_db_path))

    @staticmethod
    def _resolve_tree_node_path(tree_data, *, node_id: str) -> str | None:
        for item in tree_data.get("nodes", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("id") or "") != node_id:
                continue
            path = str(item.get("path") or "").strip()
            return path or None
        return None

    def list_users(
        self,
        *,
        q: Optional[str],
        role: Optional[str],
        status: Optional[str],
        group_id: Optional[int],
        company_id: Optional[int],
        department_id: Optional[int],
        created_from_ms: Optional[int],
        created_to_ms: Optional[int],
        manager_user_id: Optional[str],
        limit: int,
    ):
        return self._call_user_store(
            "list_users",
            **build_list_users_kwargs(
                q=q,
                role=role,
                group_id=group_id,
                company_id=company_id,
                department_id=department_id,
                status=status,
                created_from_ms=created_from_ms,
                created_to_ms=created_to_ms,
                manager_user_id=manager_user_id,
                limit=limit,
            ),
        )

    def get_user(self, user_id: str):
        return self._call_user_store("get_by_user_id", user_id)

    def create_user(
        self,
        *,
        username: str,
        password: str,
        full_name: str | None,
        email: str | None,
        manager_user_id: str | None,
        company_id: int | None,
        department_id: int | None,
        role: str,
        group_id: int | None,
        status: str,
        max_login_sessions: int | None,
        idle_timeout_minutes: int | None,
        can_change_password: bool,
        disable_login_enabled: bool,
        disable_login_until_ms: int | None,
        electronic_signature_enabled: bool,
        created_by: str,
        managed_kb_root_node_id: str | None,
    ):
        return self._call_user_store(
            "create_user",
            username=username,
            password=password,
            full_name=full_name,
            email=email,
            manager_user_id=manager_user_id,
            company_id=company_id,
            department_id=department_id,
            role=role,
            group_id=group_id,
            status=status,
            max_login_sessions=max_login_sessions,
            idle_timeout_minutes=idle_timeout_minutes,
            can_change_password=can_change_password,
            disable_login_enabled=disable_login_enabled,
            disable_login_until_ms=disable_login_until_ms,
            electronic_signature_enabled=electronic_signature_enabled,
            created_by=created_by,
            managed_kb_root_node_id=managed_kb_root_node_id,
        )

    def update_user(
        self,
        *,
        user_id: str,
        full_name: str | None,
        email: str | None,
        manager_user_id: str | None,
        company_id: int | None,
        department_id: int | None,
        role: str | None,
        group_id: int | None,
        status: str | None,
        max_login_sessions: int | None,
        idle_timeout_minutes: int | None,
        can_change_password: bool | None,
        disable_login_enabled: bool | None,
        disable_login_until_ms: int | None,
        electronic_signature_enabled: bool | None,
        managed_kb_root_node_id: str | None,
    ):
        return self._call_user_store(
            "update_user",
            user_id=user_id,
            full_name=full_name,
            email=email,
            manager_user_id=manager_user_id,
            company_id=company_id,
            department_id=department_id,
            role=role,
            group_id=group_id,
            status=status,
            max_login_sessions=max_login_sessions,
            idle_timeout_minutes=idle_timeout_minutes,
            can_change_password=can_change_password,
            disable_login_enabled=disable_login_enabled,
            disable_login_until_ms=disable_login_until_ms,
            electronic_signature_enabled=electronic_signature_enabled,
            managed_kb_root_node_id=managed_kb_root_node_id,
        )

    def delete_user(self, user_id: str) -> bool:
        return bool(self._call_user_store("delete_user", user_id))

    def update_password(self, user_id: str, new_password: str) -> None:
        self._call_user_store("update_password", user_id, new_password)

    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None:
        self._call_user_store("set_user_permission_groups", user_id, group_ids)

    def enforce_login_session_limit(self, user_id: str, max_sessions: int) -> list[str]:
        return self._call_auth_session_store(
            "enforce_user_session_limit",
            default_factory=list,
            user_id=user_id,
            max_sessions=max_sessions,
            reserve_slots=0,
            reason="policy_limit_updated",
        )

    def get_login_session_summary(
        self,
        user_id: str,
        idle_timeout_minutes: int | None,
    ) -> dict[str, int | None]:
        return self._call_auth_session_store(
            "get_active_session_summary",
            default_factory=self._empty_login_session_summary,
            user_id=user_id,
            idle_timeout_minutes=idle_timeout_minutes,
        )

    def get_login_session_summaries(
        self,
        idle_timeout_by_user: dict[str, int | None],
    ) -> dict[str, dict[str, int | None]]:
        return self._call_auth_session_store(
            "get_active_session_summaries",
            default_factory=dict,
            idle_timeout_by_user=idle_timeout_by_user,
        )

    def get_permission_group(self, group_id: int) -> dict[str, Any] | None:
        return self._call_permission_group_store("get_group", group_id)

    def get_group_by_name(self, name: str) -> dict[str, Any] | None:
        return self._call_permission_group_store("get_group_by_name", name)

    def get_company(self, company_id: int):
        return self._call_org_structure_manager("get_company", company_id)

    def get_department(self, department_id: int):
        return self._call_org_structure_manager("get_department", department_id)

    def get_managed_kb_root_path(self, *, company_id: int | None, node_id: str | None) -> str | None:
        clean_node_id = str(node_id or "").strip()
        if company_id is None or not clean_node_id:
            return None
        store = self._build_tenant_knowledge_directory_store(company_id=company_id)
        node = store.get_node(clean_node_id)
        if not node:
            return None
        tree = KnowledgeTreeManager(store=store).snapshot([], prune_unknown=False)
        return self._resolve_tree_node_path(tree, node_id=clean_node_id)
