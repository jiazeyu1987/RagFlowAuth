from __future__ import annotations

from backend.app.dependencies import AppDependencies
from backend.app.core.chat_refs import resolve_chat_ref


class UserChatPermissionsRepo:
    def __init__(self, deps: AppDependencies):
        self._deps = deps

    def get_user(self, user_id: str):
        return self._deps.user_store.get_by_user_id(user_id)

    def get_user_chats(self, user_id: str) -> list[str]:
        return self._deps.user_chat_permission_store.get_user_chats(user_id)

    def grant_permission(self, *, user_id: str, chat_id: str, granted_by: str) -> None:
        chat_info = resolve_chat_ref(self._deps, chat_id)
        self._deps.user_chat_permission_store.grant_permission(
            user_id=user_id, chat_id=chat_info.canonical, granted_by=granted_by
        )

    def revoke_permission(self, *, user_id: str, chat_id: str) -> bool:
        chat_info = resolve_chat_ref(self._deps, chat_id)
        return bool(
            self._deps.user_chat_permission_store.revoke_permission(
                user_id=user_id, chat_id=chat_id, chat_refs=list(chat_info.variants)
            )
        )

    def revoke_all_user_permissions(self, user_id: str) -> int:
        return int(self._deps.user_chat_permission_store.revoke_all_user_permissions(user_id))

    def grant_batch_permissions(self, *, user_ids: list[str], chat_ids: list[str], granted_by: str) -> int:
        count = 0
        for chat_id in chat_ids:
            chat_info = resolve_chat_ref(self._deps, chat_id)
            for user_id in user_ids:
                self._deps.user_chat_permission_store.grant_permission(
                    user_id=user_id,
                    chat_id=chat_info.canonical,
                    granted_by=granted_by,
                )
                count += 1
        return count

    def get_permission_group(self, group_id: int):
        return self._deps.permission_group_store.get_group(group_id)
