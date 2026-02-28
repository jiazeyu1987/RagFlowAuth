from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly
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


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/permission-groups")
    async def list_permission_groups(
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        groups = service.list_groups()
        return {"ok": True, "data": groups}

    @router.get("/permission-groups/{group_id}")
    async def get_permission_group(
        group_id: int,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        group = service.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Permission group not found")
        return {"ok": True, "data": group}

    @router.post("/permission-groups")
    async def create_permission_group(
        data: PermissionGroupCreate,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        payload = data.model_dump()
        try:
            group_id = service.create_group(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if not group_id:
            raise HTTPException(status_code=400, detail="Failed to create permission group")
        return {"ok": True, "data": {"group_id": group_id}}

    @router.put("/permission-groups/{group_id}")
    async def update_permission_group(
        group_id: int,
        data: PermissionGroupUpdate,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        fields_set = set(getattr(data, "model_fields_set", set()) or set())
        if "folder_id" in fields_set and "folder_id" not in payload:
            payload["folder_id"] = None
        try:
            success = service.update_group(group_id, payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update permission group")
        return {"ok": True}

    @router.delete("/permission-groups/{group_id}")
    async def delete_permission_group(
        group_id: int,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        success = service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete permission group")
        return {"ok": True}

    @router.get("/permission-groups/resources/knowledge-bases")
    async def get_knowledge_bases(
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            kb_list = service.list_knowledge_bases()
            return {"ok": True, "data": kb_list}
        except Exception as e:
            logger.error("Failed to get knowledge bases: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": []}

    @router.get("/permission-groups/resources/knowledge-tree")
    async def get_knowledge_tree(
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            tree_data = service.list_knowledge_tree()
            return {"ok": True, "data": tree_data}
        except Exception as e:
            logger.error("Failed to get knowledge tree: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": {"nodes": [], "datasets": [], "bindings": {}}}

    @router.get("/permission-groups/resources/chats")
    async def get_chat_agents(
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            chat_list = service.list_chat_agents()
            return {"ok": True, "data": chat_list}
        except Exception as e:
            logger.error("Failed to get chat agents: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": []}

    @router.get("/permission-groups/resources/group-folders")
    async def get_group_folders(
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            return {"ok": True, "data": service.list_group_folders()}
        except Exception as e:
            logger.error("Failed to get group folders: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "data": {"folders": [], "group_bindings": {}, "root_group_count": 0}}

    @router.post("/permission-groups/folders")
    async def create_group_folder(
        data: PermissionGroupFolderCreate,
        actor: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            folder = service.create_group_folder(name=data.name, parent_id=data.parent_id, created_by=actor.sub)
            return {"ok": True, "data": folder}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.put("/permission-groups/folders/{folder_id}")
    async def update_group_folder(
        folder_id: str,
        data: PermissionGroupFolderUpdate,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        fields_set = set(getattr(data, "model_fields_set", set()) or set())
        if not fields_set:
            raise HTTPException(status_code=400, detail="missing_updates")
        payload: dict[str, object | None] = {}
        if "name" in fields_set:
            payload["name"] = data.name
        if "parent_id" in fields_set:
            payload["parent_id"] = data.parent_id
        try:
            folder = service.update_group_folder(folder_id, payload)
            return {"ok": True, "data": folder}
        except ValueError as e:
            code = str(e)
            status = 404 if code == "folder_not_found" else 400
            raise HTTPException(status_code=status, detail=code) from e

    @router.delete("/permission-groups/folders/{folder_id}")
    async def delete_group_folder(
        folder_id: str,
        _: AdminOnly,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            ok = service.delete_group_folder(folder_id)
        except ValueError as e:
            code = str(e)
            status = 404 if code == "folder_not_found" else 400
            raise HTTPException(status_code=status, detail=code) from e
        if not ok:
            raise HTTPException(status_code=404, detail="folder_not_found")
        return {"ok": True}

    return router
