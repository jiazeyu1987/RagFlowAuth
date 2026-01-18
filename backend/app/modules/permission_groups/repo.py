from __future__ import annotations

from typing import Any

from backend.app.dependencies import AppDependencies
from backend.app.core.chat_refs import resolve_chat_ref
from backend.app.core.kb_refs import resolve_kb_ref


class PermissionGroupsRepo:
    def __init__(self, deps: AppDependencies):
        self._deps = deps

    def list_groups(self) -> list[dict[str, Any]]:
        return self._deps.permission_group_store.list_groups()

    def get_group(self, group_id: int) -> dict[str, Any] | None:
        return self._deps.permission_group_store.get_group(group_id)

    def create_group(self, payload: dict[str, Any]) -> int | None:
        payload = dict(payload)
        payload["accessible_kbs"] = self._normalize_accessible_kbs(payload.get("accessible_kbs"))
        payload["accessible_chats"] = self._normalize_accessible_chats(payload.get("accessible_chats"))
        return self._deps.permission_group_store.create_group(**payload)

    def update_group(self, group_id: int, payload: dict[str, Any]) -> bool:
        payload = dict(payload)
        if "accessible_kbs" in payload:
            payload["accessible_kbs"] = self._normalize_accessible_kbs(payload.get("accessible_kbs"))
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
