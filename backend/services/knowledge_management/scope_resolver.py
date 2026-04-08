from __future__ import annotations

from typing import Any

from backend.app.core.kb_refs import resolve_kb_ref
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeManager
from backend.services.ragflow_service import RagflowService

from .contracts import KnowledgeManagementError, KnowledgeManagementScope


class KnowledgeManagementScopeResolver:
    def __init__(
        self,
        *,
        tree_manager: KnowledgeTreeManager,
        directory_store: KnowledgeDirectoryStore,
        ragflow_service: RagflowService,
    ):
        self._tree_manager = tree_manager
        self._directory_store = directory_store
        self._ragflow_service = ragflow_service

    def get_management_scope(self, user: Any) -> KnowledgeManagementScope:
        role = str(getattr(user, "role", "") or "").strip().lower()
        tree = self.full_tree(prune_unknown=False)

        if role == "admin":
            return KnowledgeManagementScope(
                mode="all",
                root_node_id=None,
                root_node_path="/",
                node_ids=frozenset(
                    str(node.get("id"))
                    for node in tree["nodes"]
                    if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("id")
                ),
                dataset_ids=frozenset(
                    str(dataset.get("id"))
                    for dataset in tree["datasets"]
                    if isinstance(dataset, dict)
                    and isinstance(dataset.get("id"), str)
                    and dataset.get("id")
                ),
            )

        if role != "sub_admin":
            return KnowledgeManagementScope("none", None, None, frozenset(), frozenset())

        root_node_id = str(getattr(user, "managed_kb_root_node_id", "") or "").strip()
        if not root_node_id:
            return KnowledgeManagementScope("none", None, None, frozenset(), frozenset())

        node_by_id = {
            str(node.get("id")): node
            for node in tree["nodes"]
            if isinstance(node, dict) and isinstance(node.get("id"), str) and node.get("id")
        }
        root_node = node_by_id.get(root_node_id)
        if not root_node:
            return KnowledgeManagementScope("none", root_node_id, None, frozenset(), frozenset())

        allowed_node_ids = frozenset(self._directory_store.expand_node_ids([root_node_id]))
        dataset_ids = frozenset(
            str(dataset.get("id"))
            for dataset in tree["datasets"]
            if isinstance(dataset, dict)
            and isinstance(dataset.get("id"), str)
            and dataset.get("id")
            and str(dataset.get("node_id") or "") in allowed_node_ids
        )
        return KnowledgeManagementScope(
            mode="subtree",
            root_node_id=root_node_id,
            root_node_path=str(root_node.get("path") or ""),
            node_ids=allowed_node_ids,
            dataset_ids=dataset_ids,
        )

    def list_visible_tree(self, user: Any) -> dict[str, Any]:
        tree = self.full_tree(prune_unknown=True)
        scope = self.get_management_scope(user)
        if scope.mode == "all":
            return tree
        if scope.mode != "subtree":
            return {"nodes": [], "datasets": [], "bindings": {}}

        nodes = [
            node
            for node in tree["nodes"]
            if isinstance(node, dict) and str(node.get("id") or "") in scope.node_ids
        ]
        datasets = [
            dataset
            for dataset in tree["datasets"]
            if isinstance(dataset, dict) and str(dataset.get("id") or "") in scope.dataset_ids
        ]
        bindings = {
            str(dataset.get("id")): dataset.get("node_id")
            for dataset in datasets
            if isinstance(dataset.get("id"), str) and dataset.get("id")
        }
        return {"nodes": nodes, "datasets": datasets, "bindings": bindings}

    def list_manageable_datasets(self, user: Any) -> list[dict[str, Any]]:
        datasets = self.list_all_datasets()
        scope = self.get_management_scope(user)
        if scope.mode == "all":
            return datasets
        if scope.mode != "subtree":
            return []
        return [dataset for dataset in datasets if str(dataset.get("id") or "") in scope.dataset_ids]

    def assert_can_manage(self, user: Any) -> KnowledgeManagementScope:
        scope = self.get_management_scope(user)
        if scope.can_manage:
            return scope
        role = str(getattr(user, "role", "") or "").strip().lower()
        if role == "sub_admin" and scope.root_node_id and not scope.root_node_path:
            raise KnowledgeManagementError("managed_kb_root_node_not_found", status_code=403)
        raise KnowledgeManagementError("no_knowledge_management_permission", status_code=403)

    def assert_node_manageable(
        self,
        user: Any,
        node_id: str | None,
        *,
        allow_none: bool = False,
    ) -> KnowledgeManagementScope:
        scope = self.assert_can_manage(user)
        if node_id is None:
            if allow_none and scope.is_admin:
                return scope
            raise KnowledgeManagementError("node_out_of_management_scope", status_code=403)
        clean_node_id = str(node_id or "").strip()
        if not clean_node_id or clean_node_id not in scope.node_ids:
            raise KnowledgeManagementError("node_out_of_management_scope", status_code=403)
        return scope

    def assert_dataset_manageable(self, user: Any, dataset_ref: str) -> tuple[KnowledgeManagementScope, str]:
        scope = self.assert_can_manage(user)
        dataset_id = self.resolve_dataset_id(dataset_ref)
        if not dataset_id:
            raise KnowledgeManagementError("dataset_not_found", status_code=404)
        if scope.is_admin or dataset_id in scope.dataset_ids:
            return scope, dataset_id
        raise KnowledgeManagementError("dataset_out_of_management_scope", status_code=403)

    def resolve_dataset_id(self, dataset_ref: str) -> str | None:
        clean_ref = str(dataset_ref or "").strip()
        if not clean_ref:
            return None
        kb_info = resolve_kb_ref(self._deps_like(), clean_ref)
        if kb_info.dataset_id:
            return kb_info.dataset_id
        for dataset in self.list_all_datasets():
            dataset_id = str(dataset.get("id") or "")
            dataset_name = str(dataset.get("name") or "")
            if clean_ref == dataset_id or clean_ref == dataset_name:
                return dataset_id
        return None

    def dataset_node_id(self, dataset_id: str) -> str | None:
        tree = self.full_tree(prune_unknown=False)
        for dataset in tree["datasets"]:
            if not isinstance(dataset, dict):
                continue
            if str(dataset.get("id") or "") == dataset_id:
                node_id = dataset.get("node_id")
                return str(node_id) if isinstance(node_id, str) and node_id else None
        return None

    def list_all_datasets(self) -> list[dict[str, Any]]:
        list_all = getattr(self._ragflow_service, "list_all_datasets", None)
        datasets = list_all() if callable(list_all) else self._ragflow_service.list_datasets()
        return [dataset for dataset in (datasets or []) if isinstance(dataset, dict)]

    def full_tree(self, *, prune_unknown: bool) -> dict[str, Any]:
        return self._tree_manager.snapshot(self.list_all_datasets(), prune_unknown=prune_unknown)

    def _deps_like(self) -> Any:
        return type("_KnowledgeDeps", (), {"ragflow_service": self._ragflow_service})()
