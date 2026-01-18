from __future__ import annotations

import logging

from fastapi import HTTPException

from backend.app.modules.user_kb_permissions.repo import UserKbPermissionsRepo

logger = logging.getLogger(__name__)


class UserKbPermissionsService:
    def __init__(self, repo: UserKbPermissionsRepo):
        self._repo = repo

    def get_user_knowledge_bases_admin(self, user_id: str) -> list[str]:
        user = self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return self._repo.get_user_kbs(user_id)

    def grant_access_admin(self, *, user_id: str, kb_id: str, granted_by: str) -> str:
        user = self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        self._repo.grant_permission(user_id=user_id, kb_id=kb_id, granted_by=granted_by)
        return user.username

    def revoke_access_admin(self, *, user_id: str, kb_id: str) -> str:
        user = self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if not self._repo.revoke_permission(user_id=user_id, kb_id=kb_id):
            raise HTTPException(status_code=404, detail="权限不存在")
        return user.username

    def batch_grant_admin(self, *, user_ids: list[str], kb_ids: list[str], granted_by: str) -> int:
        valid_user_ids: list[str] = []
        for user_id in user_ids:
            if self._repo.get_user(user_id):
                valid_user_ids.append(user_id)
            else:
                raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return self._repo.grant_batch_permissions(user_ids=valid_user_ids, kb_ids=kb_ids, granted_by=granted_by)
