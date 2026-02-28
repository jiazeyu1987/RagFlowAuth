from __future__ import annotations

from typing import Any

from .store import KnowledgeDirectoryStore


class KnowledgeDirectoryManager:
    def __init__(self, store: KnowledgeDirectoryStore):
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

    def resolve_dataset_ids_from_nodes(self, node_ids: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        expanded = self._store.expand_node_ids(node_ids)
        if not expanded:
            return []
        return self._store.list_dataset_ids_for_nodes(list(expanded))
