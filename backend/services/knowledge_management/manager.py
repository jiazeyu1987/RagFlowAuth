from __future__ import annotations

from typing import Any

from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeManager
from backend.services.ragflow_service import RagflowService

from .contracts import KnowledgeManagementScope
from .dataset_mutations import KnowledgeDatasetMutations
from .directory_actions import KnowledgeDirectoryActions
from .permission_groups import KnowledgePermissionGroupAccess
from .scope_resolver import KnowledgeManagementScopeResolver


class KnowledgeManagementManager:
    def __init__(
        self,
        *,
        tree_manager: KnowledgeTreeManager,
        directory_store: KnowledgeDirectoryStore,
        ragflow_service: RagflowService,
    ):
        self._scope_resolver = KnowledgeManagementScopeResolver(
            tree_manager=tree_manager,
            directory_store=directory_store,
            ragflow_service=ragflow_service,
        )
        self._directory_actions = KnowledgeDirectoryActions(
            tree_manager=tree_manager,
            scope_resolver=self._scope_resolver,
        )
        self._dataset_mutations = KnowledgeDatasetMutations(
            ragflow_service=ragflow_service,
            scope_resolver=self._scope_resolver,
            directory_actions=self._directory_actions,
        )
        self._permission_groups = KnowledgePermissionGroupAccess(
            scope_resolver=self._scope_resolver,
        )

    def get_management_scope(self, user: Any) -> KnowledgeManagementScope:
        return self._scope_resolver.get_management_scope(user)

    def list_visible_tree(self, user: Any) -> dict[str, Any]:
        return self._scope_resolver.list_visible_tree(user)

    def list_manageable_datasets(self, user: Any) -> list[dict[str, Any]]:
        return self._scope_resolver.list_manageable_datasets(user)

    def assert_can_manage(self, user: Any) -> KnowledgeManagementScope:
        return self._scope_resolver.assert_can_manage(user)

    def assert_node_manageable(
        self,
        user: Any,
        node_id: str | None,
        *,
        allow_none: bool = False,
    ) -> KnowledgeManagementScope:
        return self._scope_resolver.assert_node_manageable(user, node_id, allow_none=allow_none)

    def assert_dataset_manageable(self, user: Any, dataset_ref: str) -> tuple[KnowledgeManagementScope, str]:
        return self._scope_resolver.assert_dataset_manageable(user, dataset_ref)

    def create_directory(
        self,
        *,
        user: Any,
        name: str,
        parent_id: str | None,
        created_by: str | None,
    ) -> dict[str, Any]:
        return self._directory_actions.create_directory(
            user=user,
            name=name,
            parent_id=parent_id,
            created_by=created_by,
        )

    def update_directory(self, *, user: Any, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._directory_actions.update_directory(user=user, node_id=node_id, payload=payload)

    def delete_directory(self, *, user: Any, node_id: str) -> bool:
        return self._directory_actions.delete_directory(user=user, node_id=node_id)

    def assign_dataset(self, *, user: Any, dataset_ref: str, node_id: str | None) -> tuple[str, str | None]:
        return self._directory_actions.assign_dataset(user=user, dataset_ref=dataset_ref, node_id=node_id)

    def create_dataset(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return self._dataset_mutations.create_dataset(user=user, payload=payload)

    def update_dataset(self, *, user: Any, dataset_ref: str, updates: dict[str, Any]) -> dict[str, Any]:
        return self._dataset_mutations.update_dataset(user=user, dataset_ref=dataset_ref, updates=updates)

    def delete_dataset(self, *, user: Any, dataset_ref: str) -> str:
        return self._dataset_mutations.delete_dataset(user=user, dataset_ref=dataset_ref)

    def prepare_dataset_create_payload(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return self._dataset_mutations.prepare_dataset_create_payload(user=user, payload=payload)

    def prepare_dataset_delete(self, *, user: Any, dataset_ref: str) -> dict[str, str]:
        return self._dataset_mutations.prepare_dataset_delete(user=user, dataset_ref=dataset_ref)

    def validate_group_kb_scope(
        self,
        *,
        user: Any,
        accessible_kbs: list[Any] | None,
        accessible_kb_nodes: list[Any] | None,
    ) -> None:
        self._permission_groups.validate_group_kb_scope(
            user=user,
            accessible_kbs=accessible_kbs,
            accessible_kb_nodes=accessible_kb_nodes,
        )

    def validate_permission_group_ids(
        self,
        *,
        user: Any,
        group_ids: list[int],
        permission_group_store: Any,
    ) -> None:
        self._permission_groups.validate_permission_group_ids(
            user=user,
            group_ids=group_ids,
            permission_group_store=permission_group_store,
        )

    def assert_permission_group_manageable(
        self,
        *,
        user: Any,
        group: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return self._permission_groups.assert_permission_group_manageable(user=user, group=group)

    def filter_manageable_permission_groups(
        self,
        *,
        user: Any,
        groups: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        return self._permission_groups.filter_manageable_permission_groups(user=user, groups=groups)

    def resolve_dataset_id(self, dataset_ref: str) -> str | None:
        return self._scope_resolver.resolve_dataset_id(dataset_ref)
