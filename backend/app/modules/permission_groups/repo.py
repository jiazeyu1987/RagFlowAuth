from __future__ import annotations

from typing import Any

from backend.app.dependencies import AppDependencies
from backend.app.core.chat_refs import resolve_chat_ref
from backend.app.core.kb_refs import resolve_kb_ref

_UNSET = object()


class PermissionGroupsRepo:
    def __init__(self, deps: AppDependencies):
        self._deps = deps

    def list_groups(self) -> list[dict[str, Any]]:
        return self._deps.permission_group_store.list_groups()

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        return self._deps.permission_group_store.get_group(group_id)

    def create_group(self, payload: dict[str, Any]) -> int | None:
        payload = dict(payload)
        payload["folder_id"] = self._normalize_folder_id(payload.get("folder_id"), allow_unset=False)
        payload["accessible_kbs"] = self._normalize_accessible_kbs(payload.get("accessible_kbs"))
        payload["accessible_kb_nodes"] = self._normalize_accessible_kb_nodes(payload.get("accessible_kb_nodes"))
        payload["accessible_chats"] = self._normalize_accessible_chats(payload.get("accessible_chats"))
        return self._deps.permission_group_store.create_group(**payload)

    def update_group(self, group_id: int, payload: dict[str, Any]) -> bool:
        payload = dict(payload)
        if "folder_id" in payload:
            payload["folder_id"] = self._normalize_folder_id(payload.get("folder_id"), allow_unset=True)
        if "accessible_kbs" in payload:
            payload["accessible_kbs"] = self._normalize_accessible_kbs(payload.get("accessible_kbs"))
        if "accessible_kb_nodes" in payload:
            payload["accessible_kb_nodes"] = self._normalize_accessible_kb_nodes(payload.get("accessible_kb_nodes"))
        if "accessible_chats" in payload:
            payload["accessible_chats"] = self._normalize_accessible_chats(payload.get("accessible_chats"))
        return bool(self._deps.permission_group_store.update_group(group_id=group_id, **payload))

    def delete_group(self, group_id: int) -> bool:
        return bool(self._deps.permission_group_store.delete_group(group_id))

    def _normalize_accessible_kbs(self, raw: Any) -> list[str] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            return []
        normalized: list[str] = []
        for ref in raw:
            if not isinstance(ref, str) or not ref:
                continue
            kb_info = resolve_kb_ref(self._deps, ref)
            normalized.append(kb_info.dataset_id or ref)

        # De-dupe preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for ref in normalized:
            if ref in seen:
                continue
            seen.add(ref)
            deduped.append(ref)
        return deduped

    def _normalize_accessible_chats(self, raw: Any) -> list[str] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            return []
        normalized: list[str] = []
        for ref in raw:
            if not isinstance(ref, str) or not ref:
                continue
            chat_info = resolve_chat_ref(self._deps, ref)
            normalized.append(chat_info.canonical)

        seen: set[str] = set()
        deduped: list[str] = []
        for ref in normalized:
            if ref in seen:
                continue
            seen.add(ref)
            deduped.append(ref)
        return deduped

    def _normalize_accessible_kb_nodes(self, raw: Any) -> list[str] | None:
        if raw is None:
            return None
        if not isinstance(raw, list):
            return []
        valid_node_ids: set[str] = set()
        loaded = False
        store = getattr(self._deps, "knowledge_directory_store", None)
        if store is not None:
            try:
                loaded = True
                valid_node_ids = {
                    str(node.get("node_id"))
                    for node in (store.list_nodes() or [])
                    if isinstance(node, dict) and isinstance(node.get("node_id"), str) and node.get("node_id")
                }
            except Exception:
                loaded = False
                valid_node_ids = set()
        normalized: list[str] = []
        for ref in raw:
            if not isinstance(ref, str):
                continue
            node_id = ref.strip()
            if not node_id:
                continue
            if loaded and node_id not in valid_node_ids:
                continue
            normalized.append(node_id)
        seen: set[str] = set()
        deduped: list[str] = []
        for ref in normalized:
            if ref in seen:
                continue
            seen.add(ref)
            deduped.append(ref)
        return deduped

    def list_knowledge_bases(self) -> list[dict[str, str]]:
        list_all = getattr(self._deps.ragflow_service, "list_all_datasets", None)
        if callable(list_all):
            datasets = list_all()
        else:
            datasets = [
                {"id": ds.get("id"), "name": ds.get("name")}
                for ds in (self._deps.ragflow_service.list_datasets() or [])
                if isinstance(ds, dict)
            ]
        return [{"id": ds["id"], "name": ds["name"]} for ds in datasets if ds.get("id") and ds.get("name")]

    def list_knowledge_tree(self) -> dict[str, Any]:
        datasets = self.list_knowledge_bases()
        manager = getattr(self._deps, "knowledge_directory_manager", None)
        if manager is None:
            return {"nodes": [], "datasets": datasets, "bindings": {}}
        try:
            return manager.snapshot(datasets, prune_unknown=True)
        except Exception:
            return {"nodes": [], "datasets": datasets, "bindings": {}}

    def list_group_folders(self) -> dict[str, Any]:
        groups = self.list_groups()
        manager = getattr(self._deps, "permission_group_folder_manager", None)
        if manager is None:
            return {"folders": [], "group_bindings": {}, "root_group_count": len(groups)}
        try:
            return manager.snapshot(groups)
        except Exception:
            return {"folders": [], "group_bindings": {}, "root_group_count": len(groups)}

    def create_group_folder(self, name: str, parent_id: str | None, *, created_by: str | None) -> dict[str, Any]:
        store = getattr(self._deps, "permission_group_folder_store", None)
        if store is None:
            raise ValueError("folder_store_unavailable")
        folder = store.create_folder(name=name, parent_id=parent_id, created_by=created_by)
        return {
            "id": folder["folder_id"],
            "name": folder["name"],
            "parent_id": folder.get("parent_id"),
        }

    def update_group_folder(self, folder_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        store = getattr(self._deps, "permission_group_folder_store", None)
        if store is None:
            raise ValueError("folder_store_unavailable")
        updates: dict[str, Any] = {}
        if "name" in payload:
            updates["name"] = payload.get("name")
        if "parent_id" in payload:
            updates["parent_id"] = payload.get("parent_id")
        folder = store.update_folder(folder_id, **updates)
        return {
            "id": folder["folder_id"],
            "name": folder["name"],
            "parent_id": folder.get("parent_id"),
        }

    def delete_group_folder(self, folder_id: str) -> bool:
        store = getattr(self._deps, "permission_group_folder_store", None)
        if store is None:
            raise ValueError("folder_store_unavailable")
        return bool(store.delete_folder(folder_id))

    def _normalize_folder_id(self, raw: Any, *, allow_unset: bool) -> str | None | object:
        if raw is _UNSET and allow_unset:
            return _UNSET
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError("invalid_folder_id")
        folder_id = raw.strip()
        if not folder_id:
            return None
        store = getattr(self._deps, "permission_group_folder_store", None)
        if store is not None and not store.folder_exists(folder_id):
            raise ValueError("folder_not_found")
        return folder_id

    def list_chat_agents(self) -> list[dict[str, str]]:
        chats = self._deps.ragflow_chat_service.list_chats(page_size=1000)
        agents = self._deps.ragflow_chat_service.list_agents(page_size=1000)

        if not isinstance(chats, list):
            chats = []
        if not isinstance(agents, list):
            agents = []

        chat_list: list[dict[str, str]] = []
        for chat in chats or []:
            if isinstance(chat, dict) and chat.get("id") and chat.get("name"):
                chat_list.append({"id": f"chat_{chat['id']}", "name": chat["name"], "type": "chat"})

        for agent in agents or []:
            if isinstance(agent, dict) and agent.get("id") and agent.get("name"):
                chat_list.append({"id": f"agent_{agent['id']}", "name": agent["name"], "type": "agent"})

        return chat_list
