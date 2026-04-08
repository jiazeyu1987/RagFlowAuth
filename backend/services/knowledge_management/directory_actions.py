from __future__ import annotations

from typing import Any

from backend.services.knowledge_tree import KnowledgeTreeError, KnowledgeTreeManager

from .contracts import KnowledgeManagementError
from .scope_resolver import KnowledgeManagementScopeResolver


class KnowledgeDirectoryActions:
    def __init__(
        self,
        *,
        tree_manager: KnowledgeTreeManager,
        scope_resolver: KnowledgeManagementScopeResolver,
    ):
        self._tree_manager = tree_manager
        self._scope_resolver = scope_resolver

    def create_directory(
        self,
        *,
        user: Any,
        name: str,
        parent_id: str | None,
        created_by: str | None,
    ) -> dict[str, Any]:
        scope = self._scope_resolver.assert_can_manage(user)
        if scope.mode == "subtree" and not parent_id:
            raise KnowledgeManagementError("parent_node_required_for_sub_admin", status_code=400)
        if parent_id:
            self._scope_resolver.assert_node_manageable(user, parent_id)
        try:
            return self._tree_manager.create_node(name=name, parent_id=parent_id, created_by=created_by)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def update_directory(self, *, user: Any, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        scope = self._scope_resolver.assert_node_manageable(user, node_id)
        if "parent_id" in payload:
            next_parent_id = payload.get("parent_id")
            if scope.mode == "subtree" and not next_parent_id:
                raise KnowledgeManagementError("parent_node_required_for_sub_admin", status_code=400)
            if next_parent_id:
                self._scope_resolver.assert_node_manageable(user, str(next_parent_id))
        try:
            return self._tree_manager.update_node(node_id=node_id, payload=payload)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def delete_directory(self, *, user: Any, node_id: str) -> bool:
        self._scope_resolver.assert_node_manageable(user, node_id)
        try:
            return self._tree_manager.delete_node(node_id)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def assign_dataset(self, *, user: Any, dataset_ref: str, node_id: str | None) -> tuple[str, str | None]:
        scope = self._scope_resolver.assert_can_manage(user)
        dataset_id = self._scope_resolver.resolve_dataset_id(dataset_ref)
        if not dataset_id:
            raise KnowledgeManagementError("dataset_not_found", status_code=404)

        current_node_id = self._scope_resolver.dataset_node_id(dataset_id)
        if current_node_id and not scope.is_admin and current_node_id not in scope.node_ids:
            raise KnowledgeManagementError("dataset_out_of_management_scope", status_code=403)

        if scope.mode == "subtree" and not node_id:
            raise KnowledgeManagementError("target_node_required_for_sub_admin", status_code=400)
        if node_id:
            self._scope_resolver.assert_node_manageable(user, node_id)
        elif not scope.is_admin:
            raise KnowledgeManagementError("node_out_of_management_scope", status_code=403)

        try:
            self._tree_manager.assign_dataset(dataset_id=dataset_id, node_id=node_id)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc
        return dataset_id, node_id
