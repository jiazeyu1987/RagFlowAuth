from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .store import ChatOwnershipStore


@dataclass
class ChatManagementError(Exception):
    code: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.code


class ChatManagementManager:
    def __init__(
        self,
        *,
        store: ChatOwnershipStore,
        ragflow_chat_service: Any,
        knowledge_management_manager: Any,
    ):
        self._store = store
        self._ragflow_chat_service = ragflow_chat_service
        self._knowledge_management_manager = knowledge_management_manager

    def list_auto_granted_chat_refs(self, user: Any) -> frozenset[str]:
        if self._role(user) != "sub_admin":
            return frozenset()
        try:
            self.assert_sub_admin_can_manage(user)
        except ChatManagementError:
            return frozenset()
        return frozenset(f"chat_{chat_id}" for chat_id in self.list_manageable_chat_ids(user))

    def list_manageable_chat_ids(self, user: Any) -> set[str]:
        role = self._role(user)
        if role == "admin":
            return {
                str(chat.get("id") or "").strip()
                for chat in self._list_all_chats()
                if isinstance(chat, dict) and str(chat.get("id") or "").strip()
            }
        self.assert_sub_admin_can_manage(user)
        return self._owned_chat_ids(user)

    def list_manageable_chats(self, user: Any) -> list[dict[str, Any]]:
        owned_ids = self.list_manageable_chat_ids(user)
        return [
            chat
            for chat in self._list_all_chats()
            if str(chat.get("id") or "").strip() in owned_ids
        ]

    def list_manageable_chat_resources(self, user: Any) -> list[dict[str, str]]:
        resources: list[dict[str, str]] = []
        for chat in self.list_manageable_chats(user):
            chat_id = str(chat.get("id") or "").strip()
            name = str(chat.get("name") or "").strip()
            if not chat_id or not name:
                continue
            resources.append({"id": f"chat_{chat_id}", "name": name, "type": "chat"})
        return resources

    def assert_chat_manageable(self, *, user: Any, chat_id: str) -> str:
        role = self._role(user)
        clean_chat_id = str(chat_id or "").strip()
        if not clean_chat_id:
            raise ChatManagementError("chat_not_found", status_code=404)
        if role == "admin":
            return clean_chat_id
        self.assert_sub_admin_can_manage(user)
        owner_id = self._store.get_chat_owner(clean_chat_id)
        if owner_id != self._user_id(user):
            raise ChatManagementError("chat_out_of_management_scope", status_code=403)
        return clean_chat_id

    def validate_chat_payload(self, *, user: Any, payload: dict[str, Any]) -> None:
        if self._role(user) == "admin":
            return
        self.assert_sub_admin_can_manage(user)
        dataset_ids = self._extract_dataset_ids(payload)
        seen: set[str] = set()
        for dataset_id in dataset_ids:
            clean_dataset_id = str(dataset_id or "").strip()
            if not clean_dataset_id or clean_dataset_id in seen:
                continue
            seen.add(clean_dataset_id)
            try:
                self._knowledge_management_manager.assert_dataset_manageable(user, clean_dataset_id)
            except Exception as exc:
                raise self._coerce_error(exc) from exc

    def record_created_chat(self, *, user: Any, chat: dict[str, Any]) -> str:
        chat_id = str((chat or {}).get("id") or "").strip()
        if not chat_id:
            raise ChatManagementError("chat_not_found", status_code=404)
        try:
            self._store.save_chat_owner(chat_id=chat_id, created_by=self._user_id(user))
        except ValueError as exc:
            raise ChatManagementError(str(exc) or "chat_ownership_record_failed", status_code=500) from exc
        return chat_id

    def cleanup_deleted_chat(self, chat_id: str) -> None:
        clean_chat_id = str(chat_id or "").strip()
        if not clean_chat_id:
            return
        self._store.delete_chat(clean_chat_id)

    def validate_group_chat_scope(
        self,
        *,
        user: Any,
        accessible_chats: list[Any] | None,
    ) -> None:
        if self._role(user) == "admin":
            return
        self.assert_sub_admin_can_manage(user)
        allowed_refs = {
            str(item.get("id") or "").strip()
            for item in self.list_manageable_chat_resources(user)
            if isinstance(item, dict)
        }
        for raw_ref in accessible_chats or []:
            if not isinstance(raw_ref, str) or not raw_ref.strip():
                continue
            canonical = self._normalize_chat_ref(raw_ref.strip())
            if not canonical.startswith("chat_") or canonical not in allowed_refs:
                raise ChatManagementError("chat_out_of_management_scope", status_code=403)

    def assert_permission_group_manageable(self, *, user: Any, group: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(group, dict):
            raise ChatManagementError("permission_group_not_found", status_code=404)
        try:
            self.validate_group_chat_scope(user=user, accessible_chats=group.get("accessible_chats"))
        except ChatManagementError as exc:
            if exc.code == "permission_group_not_found":
                raise
            raise ChatManagementError("permission_group_out_of_management_scope", status_code=403) from exc
        return group

    def filter_manageable_permission_groups(
        self,
        *,
        user: Any,
        groups: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        if self._role(user) == "admin":
            return [group for group in groups or [] if isinstance(group, dict)]

        try:
            self.assert_sub_admin_can_manage(user)
        except ChatManagementError:
            return []

        allowed_refs = {
            str(item.get("id") or "").strip()
            for item in self.list_manageable_chat_resources(user)
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        manageable: list[dict[str, Any]] = []
        for group in groups or []:
            try:
                if not isinstance(group, dict):
                    raise ChatManagementError("permission_group_not_found", status_code=404)
                if self._group_chats_within_scope(group=group, allowed_refs=allowed_refs):
                    manageable.append(group)
            except ChatManagementError:
                continue
        return manageable

    def validate_permission_group_ids(self, *, user: Any, group_ids: list[int], permission_group_store: Any) -> None:
        for group_id in group_ids:
            group = permission_group_store.get_group(int(group_id))
            if not group:
                raise ChatManagementError(f"permission_group_not_found:{group_id}", status_code=400)
            self.assert_permission_group_manageable(user=user, group=group)

    def _group_chats_within_scope(self, *, group: dict[str, Any], allowed_refs: set[str]) -> bool:
        for raw_ref in group.get("accessible_chats") or []:
            if not isinstance(raw_ref, str):
                continue
            ref = raw_ref.strip()
            if not ref:
                continue
            canonical = self._normalize_chat_ref(ref)
            if not canonical.startswith("chat_") or canonical not in allowed_refs:
                return False
        return True

    def assert_sub_admin_can_manage(self, user: Any) -> Any:
        if self._role(user) != "sub_admin":
            raise ChatManagementError("sub_admin_chat_management_required", status_code=403)
        try:
            return self._knowledge_management_manager.assert_can_manage(user)
        except Exception as exc:
            raise self._coerce_error(exc) from exc

    def _list_all_chats(self) -> list[dict[str, Any]]:
        chats = self._ragflow_chat_service.list_chats(page_size=1000)
        if not isinstance(chats, list):
            raise ChatManagementError("chat_list_invalid_response", status_code=502)
        out: list[dict[str, Any]] = []
        for chat in chats:
            if isinstance(chat, dict):
                out.append(chat)
        return out

    def _extract_dataset_ids(self, payload: dict[str, Any]) -> list[str]:
        extractor = getattr(self._ragflow_chat_service, "_extract_dataset_ids", None)
        if callable(extractor):
            extracted = extractor(payload)
            if isinstance(extracted, list):
                return [str(item or "").strip() for item in extracted if str(item or "").strip()]
        return []

    def _normalize_chat_ref(self, ref: str) -> str:
        normalizer = getattr(self._ragflow_chat_service, "normalize_chat_ref", None)
        if callable(normalizer):
            try:
                normalized = normalizer(ref)
            except Exception:
                normalized = ref
            if isinstance(normalized, str) and normalized.strip():
                return normalized.strip()
        return str(ref or "").strip()

    def _owned_chat_ids(self, user: Any) -> set[str]:
        return set(self._store.list_chat_ids_by_owner(self._user_id(user)))

    @staticmethod
    def _role(user: Any) -> str:
        return str(getattr(user, "role", "") or "").strip().lower()

    @staticmethod
    def _user_id(user: Any) -> str:
        clean_user_id = str(getattr(user, "user_id", "") or "").strip()
        if not clean_user_id:
            raise ChatManagementError("chat_owner_required", status_code=500)
        return clean_user_id

    @staticmethod
    def _coerce_error(exc: Exception) -> ChatManagementError:
        return ChatManagementError(
            str(exc) or "chat_management_failed",
            status_code=int(getattr(exc, "status_code", 403) or 403),
        )
