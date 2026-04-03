from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.core.kb_refs import resolve_kb_ref
from backend.services.knowledge_directory.store import KnowledgeDirectoryStore
from backend.services.knowledge_tree import KnowledgeTreeError, KnowledgeTreeManager
from backend.services.ragflow_service import RagflowService


@dataclass(frozen=True)
class KnowledgeManagementScope:
    mode: str
    root_node_id: str | None
    root_node_path: str | None
    node_ids: frozenset[str]
    dataset_ids: frozenset[str]

    @property
    def can_manage(self) -> bool:
        return self.mode in {"all", "subtree"}

    @property
    def is_admin(self) -> bool:
        return self.mode == "all"


@dataclass
class KnowledgeManagementError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class KnowledgeManagementManager:
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
        tree = self._full_tree(prune_unknown=False)

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
                    if isinstance(dataset, dict) and isinstance(dataset.get("id"), str) and dataset.get("id")
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
        tree = self._full_tree(prune_unknown=True)
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
        datasets = self._list_all_datasets()
        scope = self.get_management_scope(user)
        if scope.mode == "all":
            return datasets
        if scope.mode != "subtree":
            return []
        return [dataset for dataset in datasets if str(dataset.get("id") or "") in scope.dataset_ids]

    def assert_can_manage(self, user: Any) -> KnowledgeManagementScope:
        scope = self.get_management_scope(user)
        if not scope.can_manage:
            raise KnowledgeManagementError("no_knowledge_management_permission", status_code=403)
        return scope

    def assert_node_manageable(self, user: Any, node_id: str | None, *, allow_none: bool = False) -> KnowledgeManagementScope:
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
        if scope.is_admin:
            return scope, dataset_id
        if dataset_id not in scope.dataset_ids:
            raise KnowledgeManagementError("dataset_out_of_management_scope", status_code=403)
        return scope, dataset_id

    def create_directory(self, *, user: Any, name: str, parent_id: str | None, created_by: str | None) -> dict[str, Any]:
        scope = self.assert_can_manage(user)
        if scope.mode == "subtree" and not parent_id:
            raise KnowledgeManagementError("parent_node_required_for_sub_admin", status_code=400)
        if parent_id:
            self.assert_node_manageable(user, parent_id)
        try:
            return self._tree_manager.create_node(name=name, parent_id=parent_id, created_by=created_by)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def update_directory(self, *, user: Any, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        scope = self.assert_node_manageable(user, node_id)
        if "parent_id" in payload:
            next_parent_id = payload.get("parent_id")
            if scope.mode == "subtree" and not next_parent_id:
                raise KnowledgeManagementError("parent_node_required_for_sub_admin", status_code=400)
            if next_parent_id:
                self.assert_node_manageable(user, str(next_parent_id))
        try:
            return self._tree_manager.update_node(node_id=node_id, payload=payload)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def delete_directory(self, *, user: Any, node_id: str) -> bool:
        self.assert_node_manageable(user, node_id)
        try:
            return self._tree_manager.delete_node(node_id)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc

    def assign_dataset(self, *, user: Any, dataset_ref: str, node_id: str | None) -> tuple[str, str | None]:
        scope = self.assert_can_manage(user)
        dataset_id = self.resolve_dataset_id(dataset_ref)
        if not dataset_id:
            raise KnowledgeManagementError("dataset_not_found", status_code=404)
        current_node_id = self._dataset_node_id(dataset_id)
        if current_node_id and not scope.is_admin and current_node_id not in scope.node_ids:
            raise KnowledgeManagementError("dataset_out_of_management_scope", status_code=403)
        if scope.mode == "subtree" and not node_id:
            raise KnowledgeManagementError("target_node_required_for_sub_admin", status_code=400)
        if node_id:
            self.assert_node_manageable(user, node_id)
        elif not scope.is_admin:
            raise KnowledgeManagementError("node_out_of_management_scope", status_code=403)
        try:
            self._tree_manager.assign_dataset(dataset_id=dataset_id, node_id=node_id)
        except KnowledgeTreeError as exc:
            raise KnowledgeManagementError(exc.code, status_code=exc.status_code) from exc
        return dataset_id, node_id

    def create_dataset(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        body = self.prepare_dataset_create_payload(user=user, payload=payload)
        node_id = body.pop("node_id", None)

        try:
            created = self._ragflow_service.create_dataset(body)
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_create_failed", status_code=502) from exc
        if not created or not isinstance(created, dict) or not created.get("id"):
            raise KnowledgeManagementError("dataset_create_failed", status_code=500)

        if node_id:
            self.assign_dataset(user=user, dataset_ref=str(created.get("id")), node_id=str(node_id))
        return created

    def update_dataset(self, *, user: Any, dataset_ref: str, updates: dict[str, Any]) -> dict[str, Any]:
        _, dataset_id = self.assert_dataset_manageable(user, dataset_ref)
        try:
            updated = self._ragflow_service.update_dataset(dataset_id, updates)
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_update_failed", status_code=502) from exc
        if not updated:
            raise KnowledgeManagementError("dataset_update_failed", status_code=500)
        return updated

    def delete_dataset(self, *, user: Any, dataset_ref: str) -> str:
        _, dataset_id = self.assert_dataset_manageable(user, dataset_ref)
        try:
            self._ragflow_service.delete_dataset_if_empty(dataset_id)
        except ValueError as exc:
            code = str(exc) or "dataset_delete_failed"
            if code == "dataset_not_found":
                raise KnowledgeManagementError(code, status_code=404) from exc
            if code == "dataset_not_empty":
                raise KnowledgeManagementError(code, status_code=409) from exc
            raise KnowledgeManagementError(code, status_code=400) from exc
        except Exception as exc:
            raise KnowledgeManagementError(str(exc) or "dataset_delete_failed", status_code=502) from exc
        return dataset_id

    def prepare_dataset_create_payload(self, *, user: Any, payload: dict[str, Any]) -> dict[str, Any]:
        scope = self.assert_can_manage(user)
        body = dict(payload or {})
        node_id = body.get("node_id")
        name = str(body.get("name") or "").strip()
        if not name:
            raise KnowledgeManagementError("missing_name", status_code=400)
        body["name"] = name
        body.pop("id", None)
        body.pop("dataset_id", None)
        if scope.mode == "subtree":
            if not isinstance(node_id, str) or not node_id.strip():
                raise KnowledgeManagementError("target_node_required_for_sub_admin", status_code=400)
            self.assert_node_manageable(user, node_id)
        return body

    def prepare_dataset_delete(self, *, user: Any, dataset_ref: str) -> dict[str, str]:
        _, dataset_id = self.assert_dataset_manageable(user, dataset_ref)
        detail = self._ragflow_service.get_dataset_detail(dataset_id)
        if not detail:
            raise KnowledgeManagementError("dataset_not_found", status_code=404)
        try:
            doc_count = int(detail.get("document_count") or 0)
        except Exception:
            doc_count = 0
        try:
            chunk_count = int(detail.get("chunk_count") or 0)
        except Exception:
            chunk_count = 0
        if doc_count > 0 or chunk_count > 0:
            raise KnowledgeManagementError("dataset_not_empty", status_code=409)
        dataset_name = str(detail.get("name") or dataset_id)
        return {
            "dataset_ref": dataset_ref,
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
        }

    def validate_group_kb_scope(
        self,
        *,
        user: Any,
        accessible_kbs: list[Any] | None,
        accessible_kb_nodes: list[Any] | None,
    ) -> None:
        self.assert_can_manage(user)
        for raw_node_id in accessible_kb_nodes or []:
            if not isinstance(raw_node_id, str) or not raw_node_id.strip():
                continue
            self.assert_node_manageable(user, raw_node_id.strip())
        for raw_ref in accessible_kbs or []:
            if not isinstance(raw_ref, str) or not raw_ref.strip():
                continue
            ref = raw_ref.strip()
            if ref.startswith("node:"):
                self.assert_node_manageable(user, ref[5:].strip())
                continue
            if ref.startswith("dataset:"):
                self.assert_dataset_manageable(user, ref[8:].strip())
                continue
            self.assert_dataset_manageable(user, ref)

    def validate_permission_group_ids(self, *, user: Any, group_ids: list[int], permission_group_store: Any) -> None:
        for group_id in group_ids:
            group = permission_group_store.get_group(int(group_id))
            if not group:
                raise KnowledgeManagementError(f"permission_group_not_found:{group_id}", status_code=400)
            self.validate_group_kb_scope(
                user=user,
                accessible_kbs=group.get("accessible_kbs"),
                accessible_kb_nodes=group.get("accessible_kb_nodes"),
            )

    def resolve_dataset_id(self, dataset_ref: str) -> str | None:
        clean_ref = str(dataset_ref or "").strip()
        if not clean_ref:
            return None
        kb_info = resolve_kb_ref(self._deps_like(), clean_ref)
        if kb_info.dataset_id:
            return kb_info.dataset_id
        for dataset in self._list_all_datasets():
            dataset_id = str(dataset.get("id") or "")
            dataset_name = str(dataset.get("name") or "")
            if clean_ref == dataset_id or clean_ref == dataset_name:
                return dataset_id
        return None

    def _dataset_node_id(self, dataset_id: str) -> str | None:
        tree = self._full_tree(prune_unknown=False)
        for dataset in tree["datasets"]:
            if not isinstance(dataset, dict):
                continue
            if str(dataset.get("id") or "") == dataset_id:
                node_id = dataset.get("node_id")
                return str(node_id) if isinstance(node_id, str) and node_id else None
        return None

    def _list_all_datasets(self) -> list[dict[str, Any]]:
        list_all = getattr(self._ragflow_service, "list_all_datasets", None)
        datasets = list_all() if callable(list_all) else self._ragflow_service.list_datasets()
        out: list[dict[str, Any]] = []
        for dataset in datasets or []:
            if isinstance(dataset, dict):
                out.append(dataset)
        return out

    def _full_tree(self, *, prune_unknown: bool) -> dict[str, Any]:
        datasets = self._list_all_datasets()
        return self._tree_manager.snapshot(datasets, prune_unknown=prune_unknown)

    def _deps_like(self) -> Any:
        return type(
            "_KnowledgeDeps",
            (),
            {"ragflow_service": self._ragflow_service},
        )()
