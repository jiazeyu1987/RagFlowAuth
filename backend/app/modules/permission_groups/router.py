from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly, AuthContextDep
from backend.app.dependencies import AppDependencies

from backend.app.modules.permission_groups.schemas import (
    PermissionGroupCreate,
    PermissionGroupFolderCreate,
    PermissionGroupFolderUpdate,
    PermissionGroupUpdate,
)
from backend.app.modules.permission_groups.service import PermissionGroupsService

logger = logging.getLogger(__name__)


def get_service(deps: AppDependencies = Depends(get_deps)) -> PermissionGroupsService:
    return PermissionGroupsService(deps)


def _assert_group_management(ctx: AuthContextDep) -> None:
    if str(getattr(ctx.user, "role", "") or "").strip().lower() != "sub_admin":
        raise HTTPException(status_code=403, detail="sub_admin_only_permission_group_management")
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=403, detail="sub_admin_only_permission_group_management")
    try:
        manager.assert_can_manage(ctx.user)
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def _validate_group_scope(ctx: AuthContextDep, *, accessible_kbs, accessible_kb_nodes) -> None:
    try:
        ctx.deps.knowledge_management_manager.validate_group_kb_scope(
            user=ctx.user,
            accessible_kbs=accessible_kbs,
            accessible_kb_nodes=accessible_kb_nodes,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc


def _list_manageable_groups(ctx: AuthContextDep, service: PermissionGroupsService) -> list[dict]:
    groups = service.list_groups()
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        return []
    return manager.filter_manageable_permission_groups(user=ctx.user, groups=groups)


def _get_manageable_group(ctx: AuthContextDep, service: PermissionGroupsService, group_id: int) -> dict:
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Permission group not found")
    try:
        return ctx.deps.knowledge_management_manager.assert_permission_group_manageable(
            user=ctx.user,
            group=group,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def _visible_folder_ids(folder_snapshot: dict) -> set[str]:
    return {
        str(folder.get("id"))
        for folder in (folder_snapshot or {}).get("folders", [])
        if isinstance(folder, dict) and isinstance(folder.get("id"), str) and folder.get("id")
    }


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/permission-groups")
    async def list_permission_groups(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        groups = _list_manageable_groups(ctx, service)
        return {"ok": True, "data": groups}

    @router.get("/permission-groups/{group_id}")
    async def get_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        group = _get_manageable_group(ctx, service, group_id)
        return {"ok": True, "data": group}

    @router.post("/permission-groups")
    async def create_permission_group(
        data: PermissionGroupCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        payload = data.model_dump()
        _validate_group_scope(
            ctx,
            accessible_kbs=payload.get("accessible_kbs"),
            accessible_kb_nodes=payload.get("accessible_kb_nodes"),
        )
        group_id = service.create_group(payload)
        if not group_id:
            raise HTTPException(status_code=400, detail="Failed to create permission group")
        return {"ok": True, "data": {"group_id": group_id}}

    @router.put("/permission-groups/{group_id}")
    async def update_permission_group(
        group_id: int,
        data: PermissionGroupUpdate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        fields_set = set(getattr(data, "model_fields_set", set()) or set())
        if "folder_id" in fields_set and "folder_id" not in payload:
            payload["folder_id"] = None
        current = _get_manageable_group(ctx, service, group_id)
        merged = dict(current)
        merged.update(payload)
        _validate_group_scope(
            ctx,
            accessible_kbs=merged.get("accessible_kbs"),
            accessible_kb_nodes=merged.get("accessible_kb_nodes"),
        )
        success = service.update_group(group_id, payload)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update permission group")
        return {"ok": True}

    @router.delete("/permission-groups/{group_id}")
    async def delete_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        _get_manageable_group(ctx, service, group_id)
        success = service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete permission group")
        return {"ok": True}

    @router.get("/permission-groups/resources/knowledge-bases")
    async def get_knowledge_bases(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            kb_list = ctx.deps.knowledge_management_manager.list_manageable_datasets(ctx.user)
            return {"ok": True, "data": kb_list}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get knowledge bases: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": []}

    @router.get("/permission-groups/resources/knowledge-tree")
    async def get_knowledge_tree(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            tree_data = ctx.deps.knowledge_management_manager.list_visible_tree(ctx.user)
            return {"ok": True, "data": tree_data}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get knowledge tree: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": {"nodes": [], "datasets": [], "bindings": {}}}

    @router.get("/permission-groups/resources/chats")
    async def get_chat_agents(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            chat_list = service.list_chat_agents()
            return {"ok": True, "data": chat_list}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get chat agents: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": []}

    @router.get("/permission-groups/resources/group-folders")
    async def get_group_folders(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            groups = _list_manageable_groups(ctx, service)
            return {"ok": True, "data": service.list_group_folders(groups)}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get group folders: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": {"folders": [], "group_bindings": {}, "root_group_count": 0}}

    @router.post("/permission-groups/folders")
    async def create_group_folder(
        data: PermissionGroupFolderCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        if data.parent_id:
            folder_snapshot = service.list_group_folders(_list_manageable_groups(ctx, service))
            if data.parent_id not in _visible_folder_ids(folder_snapshot):
                raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
        folder = service.create_group_folder(name=data.name, parent_id=data.parent_id, created_by=ctx.payload.sub)
        return {"ok": True, "data": folder}

    @router.put("/permission-groups/folders/{folder_id}")
    async def update_group_folder(
        folder_id: str,
        data: PermissionGroupFolderUpdate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        folder_snapshot = service.list_group_folders(_list_manageable_groups(ctx, service))
        visible_folder_ids = _visible_folder_ids(folder_snapshot)
        if folder_id not in visible_folder_ids:
            raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
        fields_set = set(getattr(data, "model_fields_set", set()) or set())
        if not fields_set:
            raise HTTPException(status_code=400, detail="missing_updates")
        payload: dict[str, object | None] = {}
        if "name" in fields_set:
            payload["name"] = data.name
        if "parent_id" in fields_set:
            if data.parent_id and data.parent_id not in visible_folder_ids:
                raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
            payload["parent_id"] = data.parent_id
        folder = service.update_group_folder(folder_id, payload)
        return {"ok": True, "data": folder}

    @router.delete("/permission-groups/folders/{folder_id}")
    async def delete_group_folder(
        folder_id: str,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        folder_snapshot = service.list_group_folders(_list_manageable_groups(ctx, service))
        if folder_id not in _visible_folder_ids(folder_snapshot):
            raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
        ok = service.delete_group_folder(folder_id)
        if not ok:
            raise HTTPException(status_code=404, detail="folder_not_found")
        return {"ok": True}

    return router
