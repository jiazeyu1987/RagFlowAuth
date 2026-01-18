from __future__ import annotations

from typing import Any

from backend.app.dependencies import AppDependencies
from backend.app.core.kb_refs import resolve_kb_ref


class UserKbPermissionsRepo:
    def __init__(self, deps: AppDependencies):
        self._deps = deps

    def get_user(self, user_id: str):
        return self._deps.user_store.get_by_user_id(user_id)

    def get_user_kbs(self, user_id: str) -> list[str]:
        return self._deps.user_kb_permission_store.get_user_kbs(user_id)

    def grant_permission(self, *, user_id: str, kb_id: str, granted_by: str) -> None:
        kb_info = resolve_kb_ref(self._deps, kb_id)
        self._deps.user_kb_permission_store.grant_permission(
            user_id=user_id,
            kb_id=(kb_info.dataset_id or kb_id),
            granted_by=granted_by,
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or kb_id),
        )

    def revoke_permission(self, *, user_id: str, kb_id: str) -> bool:
        kb_info = resolve_kb_ref(self._deps, kb_id)
        return bool(
            self._deps.user_kb_permission_store.revoke_permission(
                user_id=user_id,
                kb_id=kb_id,
                kb_refs=list(kb_info.variants),
                kb_dataset_id=kb_info.dataset_id,
            )
        )

    def grant_batch_permissions(self, *, user_ids: list[str], kb_ids: list[str], granted_by: str) -> int:
        count = 0
        for kb_id in kb_ids:
            kb_info = resolve_kb_ref(self._deps, kb_id)
            canonical_id = kb_info.dataset_id or kb_id
            canonical_name = kb_info.name or kb_id
            for user_id in user_ids:
                self._deps.user_kb_permission_store.grant_permission(
                    user_id=user_id,
                    kb_id=canonical_id,
                    granted_by=granted_by,
                    kb_dataset_id=kb_info.dataset_id,
                    kb_name=canonical_name,
                )
                count += 1
        return count

    def get_permission_group(self, group_id: int) -> dict[str, Any] | None:
        return self._deps.permission_group_store.get_group(group_id)
