from __future__ import annotations

from typing import Any

from .contracts import KnowledgeManagementError
from .scope_resolver import KnowledgeManagementScopeResolver


class KnowledgePermissionGroupAccess:
    def __init__(self, *, scope_resolver: KnowledgeManagementScopeResolver):
        self._scope_resolver = scope_resolver

    def validate_group_kb_scope(
        self,
        *,
        user: Any,
        accessible_kbs: list[Any] | None,
        accessible_kb_nodes: list[Any] | None,
    ) -> None:
        self._scope_resolver.assert_can_manage(user)
        for raw_node_id in accessible_kb_nodes or []:
            if not isinstance(raw_node_id, str) or not raw_node_id.strip():
                continue
            self._scope_resolver.assert_node_manageable(user, raw_node_id.strip())
        for raw_ref in accessible_kbs or []:
            if not isinstance(raw_ref, str) or not raw_ref.strip():
                continue
            ref = raw_ref.strip()
            if ref.startswith("node:"):
                self._scope_resolver.assert_node_manageable(user, ref[5:].strip())
                continue
            if ref.startswith("dataset:"):
                self._scope_resolver.assert_dataset_manageable(user, ref[8:].strip())
                continue
            self._scope_resolver.assert_dataset_manageable(user, ref)

    def validate_permission_group_ids(
        self,
        *,
        user: Any,
        group_ids: list[int],
        permission_group_store: Any,
    ) -> None:
        for group_id in group_ids:
            group = permission_group_store.get_group(int(group_id))
            if not group:
                raise KnowledgeManagementError(f"permission_group_not_found:{group_id}", status_code=400)
            self.assert_permission_group_manageable(user=user, group=group)

    def assert_permission_group_manageable(
        self,
        *,
        user: Any,
        group: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(group, dict):
            raise KnowledgeManagementError("permission_group_not_found", status_code=404)
        try:
            self.validate_group_kb_scope(
                user=user,
                accessible_kbs=group.get("accessible_kbs"),
                accessible_kb_nodes=group.get("accessible_kb_nodes"),
            )
        except KnowledgeManagementError:
            raise
        except Exception as exc:
            raise KnowledgeManagementError(
                "permission_group_out_of_management_scope",
                status_code=403,
            ) from exc
        return group

    def filter_manageable_permission_groups(
        self,
        *,
        user: Any,
        groups: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        try:
            scope = self._scope_resolver.assert_can_manage(user)
        except KnowledgeManagementError:
            return []

        dataset_ref_cache: dict[str, str | None] = {}
        manageable: list[dict[str, Any]] = []
        for group in groups or []:
            try:
                if not isinstance(group, dict):
                    raise KnowledgeManagementError("permission_group_not_found", status_code=404)
                if self._is_group_within_scope(
                    group=group,
                    scope=scope,
                    dataset_ref_cache=dataset_ref_cache,
                ):
                    manageable.append(group)
            except KnowledgeManagementError:
                continue
        return manageable

    def _is_group_within_scope(
        self,
        *,
        group: dict[str, Any],
        scope: Any,
        dataset_ref_cache: dict[str, str | None],
    ) -> bool:
        for raw_node_id in group.get("accessible_kb_nodes") or []:
            if not isinstance(raw_node_id, str):
                continue
            node_id = raw_node_id.strip()
            if not node_id:
                continue
            if node_id not in scope.node_ids:
                return False

        for raw_ref in group.get("accessible_kbs") or []:
            if not isinstance(raw_ref, str):
                continue
            ref = raw_ref.strip()
            if not ref:
                continue
            if ref.startswith("node:"):
                if ref[5:].strip() not in scope.node_ids:
                    return False
                continue
            if ref.startswith("dataset:"):
                ref = ref[8:].strip()
            dataset_id = dataset_ref_cache.get(ref)
            if ref not in dataset_ref_cache:
                dataset_id = self._scope_resolver.resolve_dataset_id(ref)
                dataset_ref_cache[ref] = dataset_id
            if not dataset_id:
                return False
            if not scope.is_admin and dataset_id not in scope.dataset_ids:
                return False

        return True
