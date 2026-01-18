from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies

from backend.app.modules.user_kb_permissions.repo import UserKbPermissionsRepo
from backend.app.modules.user_kb_permissions.schemas import BatchGrantRequest, KbListResponse
from backend.app.modules.user_kb_permissions.service import UserKbPermissionsService


router = APIRouter()
logger = logging.getLogger(__name__)
perm_logger = logging.getLogger("uvicorn.error")


def get_service(deps: AppDependencies = Depends(get_deps)) -> UserKbPermissionsService:
    return UserKbPermissionsService(UserKbPermissionsRepo(deps))


@router.get("/users/{user_id}/kbs", response_model=KbListResponse)
async def get_user_knowledge_bases(
    user_id: str,
    _: AdminOnly,
    service: UserKbPermissionsService = Depends(get_service),
):
    kb_ids = service.get_user_knowledge_bases_admin(user_id)
    return KbListResponse(kb_ids=kb_ids)


@router.post("/users/{user_id}/kbs/{kb_id}", status_code=201)
async def grant_knowledge_base_access(
    user_id: str,
    kb_id: str,
    payload: AdminOnly,
    service: UserKbPermissionsService = Depends(get_service),
):
    username = service.grant_access_admin(user_id=user_id, kb_id=kb_id, granted_by=payload.sub)
    return {"message": f"已授予用户 {username} 访问知识库 '{kb_id}' 的权限"}


@router.delete("/users/{user_id}/kbs/{kb_id}")
async def revoke_knowledge_base_access(
    user_id: str,
    kb_id: str,
    _: AdminOnly,
    service: UserKbPermissionsService = Depends(get_service),
):
    username = service.revoke_access_admin(user_id=user_id, kb_id=kb_id)
    return {"message": f"已撤销用户 {username} 访问知识库 '{kb_id}' 的权限"}


@router.get("/me/kbs", response_model=KbListResponse)
async def get_my_knowledge_bases(
    ctx: AuthContextDep,
):
    if ctx.snapshot.is_admin:
        return KbListResponse(kb_ids=ctx.deps.ragflow_service.list_all_kb_names())

    try:
        perm_logger.info(
            "[PERMDBG] /api/me/kbs user=%s role=%s kb_scope=%s kb_refs=%s",
            ctx.user.username,
            ctx.user.role,
            ctx.snapshot.kb_scope,
            sorted(list(ctx.snapshot.kb_names))[:50],
        )
    except Exception:
        pass

    ragflow_service = ctx.deps.ragflow_service
    resolve_names = getattr(ragflow_service, "resolve_dataset_names", None)
    if callable(resolve_names):
        try:
            names = resolve_names(list(ctx.snapshot.kb_names))
            return KbListResponse(kb_ids=sorted(set(names)))
        except Exception:
            pass
    return KbListResponse(kb_ids=sorted(ctx.snapshot.kb_names))


@router.post("/users/batch-grant")
async def batch_grant_knowledge_bases(
    request_data: BatchGrantRequest,
    payload: AdminOnly,
    service: UserKbPermissionsService = Depends(get_service),
):
    count = service.batch_grant_admin(user_ids=request_data.user_ids, kb_ids=request_data.kb_ids, granted_by=payload.sub)
    return {
        "message": f"已为 {len(request_data.user_ids)} 个用户授予 {len(request_data.kb_ids)} 个知识库的权限",
        "total_permissions": count,
    }
