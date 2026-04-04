from __future__ import annotations

from typing import Any, Optional

from backend.app.dependencies import AppDependencies
from backend.database.schema_migrations import ensure_schema
from backend.database.tenant_paths import resolve_tenant_auth_db_path
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeManager


class UsersRepo:
    def __init__(self, deps: AppDependencies, *, permission_group_store=None):
        self._deps = deps
        self._permission_group_store = permission_group_store or getattr(deps, "permission_group_store", None)

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
        return self._deps.user_store.list_users(
            q=q,
            role=role,
            status=status,
            group_id=group_id,
            company_id=company_id,
            department_id=department_id,
            created_from_ms=created_from_ms,
            created_to_ms=created_to_ms,
            manager_user_id=manager_user_id,
            limit=limit,
        )

    def get_user(self, user_id: str):
        return self._deps.user_store.get_by_user_id(user_id)

    def create_user(self, **kwargs):
        return self._deps.user_store.create_user(**kwargs)

    def update_user(self, **kwargs):
        return self._deps.user_store.update_user(**kwargs)

    def delete_user(self, user_id: str) -> bool:
        return bool(self._deps.user_store.delete_user(user_id))

    def update_password(self, user_id: str, new_password: str) -> None:
        self._deps.user_store.update_password(user_id, new_password)

    def set_user_permission_groups(self, user_id: str, group_ids: list[int]) -> None:
        self._deps.user_store.set_user_permission_groups(user_id, group_ids)

    def enforce_login_session_limit(self, user_id: str, max_sessions: int) -> list[str]:
        store = getattr(self._deps, "auth_session_store", None)
        if not store:
            return []
        return store.enforce_user_session_limit(
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
        store = getattr(self._deps, "auth_session_store", None)
        if not store:
            return {
                "active_session_count": 0,
                "active_session_last_activity_at_ms": None,
            }
        return store.get_active_session_summary(
            user_id=user_id,
            idle_timeout_minutes=idle_timeout_minutes,
        )

    def get_login_session_summaries(
        self,
        idle_timeout_by_user: dict[str, int | None],
    ) -> dict[str, dict[str, int | None]]:
        store = getattr(self._deps, "auth_session_store", None)
        if not store:
            return {}
        return store.get_active_session_summaries(idle_timeout_by_user=idle_timeout_by_user)

    def get_permission_group(self, group_id: int) -> dict[str, Any] | None:
        if self._permission_group_store is None:
            return None
        return self._permission_group_store.get_group(group_id)

    def get_group_by_name(self, name: str) -> dict[str, Any] | None:
        if self._permission_group_store is None:
            return None
        return self._permission_group_store.get_group_by_name(name)

    def get_company(self, company_id: int):
        return self._deps.org_structure_manager.get_company(company_id)

    def get_department(self, department_id: int):
        return self._deps.org_structure_manager.get_department(department_id)

    def get_managed_kb_root_path(self, *, company_id: int | None, node_id: str | None) -> str | None:
        clean_node_id = str(node_id or "").strip()
        if company_id is None or not clean_node_id:
            return None
        tenant_db_path = resolve_tenant_auth_db_path(
            company_id=company_id,
            base_db_path=getattr(self._deps.user_store, "db_path", None),
        )
        ensure_schema(str(tenant_db_path))
        store = KnowledgeDirectoryStore(db_path=str(tenant_db_path))
        node = store.get_node(clean_node_id)
        if not node:
            return None
        tree = KnowledgeTreeManager(store=store).snapshot([], prune_unknown=False)
        for item in tree.get("nodes", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("id") or "") == clean_node_id:
                path = str(item.get("path") or "").strip()
                return path or None
        return None
