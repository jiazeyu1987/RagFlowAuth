from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class KnowledgeTreePort(Protocol):
    def list_nodes(self) -> list[dict[str, Any]]: ...
    def list_bindings(self) -> dict[str, str]: ...
    def remove_bindings_for_unknown_datasets(self, known_dataset_ids: set[str]) -> int: ...
    def expand_node_ids(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> set[str]: ...
    def list_dataset_ids_for_nodes(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> list[str]: ...
    def create_node(self, name: str, parent_id: str | None, *, created_by: str | None = None) -> dict[str, Any]: ...
    def update_node(
        self,
        node_id: str,
        *,
        name: str | None | object = ...,
        parent_id: str | None | object = ...,
    ) -> dict[str, Any]: ...
    def delete_node(self, node_id: str) -> bool: ...
    def assign_dataset(self, dataset_id: str, node_id: str | None) -> None: ...


@dataclass
class KnowledgeTreeError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class KnowledgeTreeManager:
    def __init__(self, store: KnowledgeTreePort):
        self._store = store

    def snapshot(self, datasets: list[dict[str, Any]], *, prune_unknown: bool = False) -> dict[str, Any]:
        dataset_items: list[dict[str, Any]] = []
        known_dataset_ids: set[str] = set()
        for ds in datasets or []:
            if not isinstance(ds, dict):
                continue
            dataset_id = ds.get("id")
            name = ds.get("name")
            if not isinstance(dataset_id, str) or not dataset_id:
                continue
            if not isinstance(name, str) or not name:
                continue
            known_dataset_ids.add(dataset_id)
            dataset_items.append({"id": dataset_id, "name": name})

        if prune_unknown and known_dataset_ids:
            self._store.remove_bindings_for_unknown_datasets(known_dataset_ids)

        nodes = self._store.list_nodes()
        bindings = self._store.list_bindings()
        node_map = {str(node["node_id"]): node for node in nodes if node.get("node_id")}

        path_cache: dict[str, str] = {}

        def node_path(node_id: str | None) -> str:
            if not node_id:
                return "/"
            if node_id in path_cache:
                return path_cache[node_id]
            parts: list[str] = []
            guard: set[str] = set()
            cur_id = node_id
            while cur_id and cur_id not in guard:
                guard.add(cur_id)
                node = node_map.get(cur_id)
                if not node:
                    break
                name = str(node.get("name") or "").strip()
                if name:
                    parts.append(name)
                parent = node.get("parent_id")
                cur_id = str(parent) if isinstance(parent, str) and parent else None
            path = "/" + "/".join(reversed(parts)) if parts else "/"
            path_cache[node_id] = path
            return path

        out_nodes = []
        for node in nodes:
            node_id = str(node.get("node_id") or "")
            if not node_id:
                continue
            out_nodes.append(
                {
                    "id": node_id,
                    "name": str(node.get("name") or ""),
                    "parent_id": node.get("parent_id"),
                    "path": node_path(node_id),
                    "created_by": node.get("created_by"),
                    "created_at_ms": node.get("created_at_ms"),
                    "updated_at_ms": node.get("updated_at_ms"),
                }
            )

        out_datasets = []
        for ds in dataset_items:
            dataset_id = ds["id"]
            node_id = bindings.get(dataset_id)
            out_datasets.append(
                {
                    "id": dataset_id,
                    "name": ds["name"],
                    "node_id": node_id,
                    "node_path": node_path(node_id),
                }
            )

        return {
            "nodes": out_nodes,
            "datasets": out_datasets,
            "bindings": bindings,
        }

    def trim_tree_for_non_admin(self, tree: dict[str, Any]) -> dict[str, Any]:
        nodes = [node for node in (tree.get("nodes") or []) if isinstance(node, dict)]
        datasets = [ds for ds in (tree.get("datasets") or []) if isinstance(ds, dict)]
        node_by_id = {str(node.get("id")): node for node in nodes if isinstance(node.get("id"), str)}

        keep_node_ids: set[str] = set()
        for ds in datasets:
            node_id = ds.get("node_id")
            cur = str(node_id) if isinstance(node_id, str) and node_id else None
            guard: set[str] = set()
            while cur and cur not in guard:
                guard.add(cur)
                keep_node_ids.add(cur)
                node = node_by_id.get(cur)
                if not node:
                    break
                parent_id = node.get("parent_id")
                cur = str(parent_id) if isinstance(parent_id, str) and parent_id else None

        return {
            "nodes": [node for node in nodes if str(node.get("id") or "") in keep_node_ids],
            "datasets": datasets,
            "bindings": {
                str(ds.get("id")): ds.get("node_id")
                for ds in datasets
                if isinstance(ds.get("id"), str) and ds.get("id")
            },
        }

    def resolve_dataset_ids_from_nodes(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        expanded = self._store.expand_node_ids(node_ids)
        if not expanded:
            return []
        return self._store.list_dataset_ids_for_nodes(list(expanded))

    def create_node(self, *, name: str, parent_id: str | None, created_by: str | None) -> dict[str, Any]:
        try:
            node = self._store.create_node(name=name, parent_id=parent_id, created_by=created_by)
        except ValueError as e:
            raise KnowledgeTreeError(str(e), status_code=400) from e
        return {"id": node["node_id"], "name": node["name"], "parent_id": node.get("parent_id")}

    def update_node(self, *, node_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        fields_set = set(payload.keys())
        if not fields_set:
            raise KnowledgeTreeError("missing_updates", status_code=400)
        updates: dict[str, Any] = {}
        if "name" in fields_set:
            updates["name"] = payload.get("name")
        if "parent_id" in fields_set:
            updates["parent_id"] = payload.get("parent_id")
        try:
            node = self._store.update_node(node_id, **updates)
        except ValueError as e:
            code = str(e)
            status = 404 if code == "node_not_found" else 400
            raise KnowledgeTreeError(code, status_code=status) from e
        return {"id": node["node_id"], "name": node["name"], "parent_id": node.get("parent_id")}

    def delete_node(self, node_id: str) -> bool:
        try:
            ok = self._store.delete_node(node_id)
        except ValueError as e:
            raise KnowledgeTreeError(str(e), status_code=400) from e
        if not ok:
            raise KnowledgeTreeError("node_not_found", status_code=404)
        return True

    def assign_dataset(self, *, dataset_id: str, node_id: str | None) -> None:
        try:
            self._store.assign_dataset(dataset_id, node_id)
        except ValueError as e:
            code = str(e)
            status = 404 if code == "node_not_found" else 400
            raise KnowledgeTreeError(code, status_code=status) from e
