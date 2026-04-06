from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import get_deps
from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import group_tool_scope_within_snapshot
from backend.app.dependencies import AppDependencies
from backend.models.auth import ResultEnvelope
from backend.models.permission_group import (
    PermissionGroupChatsEnvelope,
    PermissionGroupCreateResultEnvelope,
    PermissionGroupEnvelope,
    PermissionGroupFolderEnvelope,
    PermissionGroupFolderSnapshotEnvelope,
    PermissionGroupKnowledgeBasesEnvelope,
    PermissionGroupKnowledgeTreeEnvelope,
    PermissionGroupListEnvelope,
)

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


def _require_object_payload(value: object, *, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HTTPException(status_code=502, detail=detail)
    return value


def _require_object_list(value: object, *, detail: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=502, detail=detail)
    for item in value:
        if not isinstance(item, dict):
            raise HTTPException(status_code=502, detail=detail)
    return value


def _require_knowledge_tree(value: object, *, detail: str) -> dict[str, Any]:
    payload = _require_object_payload(value, detail=detail)
    if not isinstance(payload.get("nodes"), list) or not isinstance(payload.get("datasets"), list):
        raise HTTPException(status_code=502, detail=detail)
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise HTTPException(status_code=502, detail=detail)
    _require_object_list(payload["nodes"], detail=detail)
    _require_object_list(payload["datasets"], detail=detail)
    return payload


def _require_folder_snapshot(value: object, *, detail: str) -> dict[str, Any]:
    payload = _require_object_payload(value, detail=detail)
    folders = payload.get("folders")
    group_bindings = payload.get("group_bindings")
    root_group_count = payload.get("root_group_count")
    _require_object_list(folders, detail=detail)
    if not isinstance(group_bindings, dict):
        raise HTTPException(status_code=502, detail=detail)
    if not isinstance(root_group_count, int) or isinstance(root_group_count, bool):
        raise HTTPException(status_code=502, detail=detail)
    for key, folder_id in group_bindings.items():
        if not isinstance(key, str):
            raise HTTPException(status_code=502, detail=detail)
        if folder_id is not None and not isinstance(folder_id, str):
            raise HTTPException(status_code=502, detail=detail)
    return payload


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


def _chat_management_manager(ctx: AuthContextDep):
    manager = getattr(ctx.deps, "chat_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="chat_management_manager_unavailable")
    return manager


def _validate_group_scope(ctx: AuthContextDep, *, accessible_kbs, accessible_kb_nodes, accessible_chats) -> None:
    try:
        ctx.deps.knowledge_management_manager.validate_group_kb_scope(
            user=ctx.user,
            accessible_kbs=accessible_kbs,
            accessible_kb_nodes=accessible_kb_nodes,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc
    try:
        _chat_management_manager(ctx).validate_group_chat_scope(
            user=ctx.user,
            accessible_chats=accessible_chats,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 400) or 400), detail=str(exc)) from exc


def _list_manageable_groups(ctx: AuthContextDep, service: PermissionGroupsService) -> list[dict]:
    groups = _require_object_list(service.list_groups(), detail="permission_group_list_invalid_payload")
    groups = service.filter_manageable_groups(user=ctx.user, groups=groups)
    groups = _require_object_list(groups, detail="permission_group_list_invalid_payload")
    manager = getattr(ctx.deps, "knowledge_management_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="knowledge_management_manager_unavailable")
    groups = manager.filter_manageable_permission_groups(user=ctx.user, groups=groups)
    groups = _require_object_list(groups, detail="permission_group_list_invalid_payload")
    groups = _chat_management_manager(ctx).filter_manageable_permission_groups(user=ctx.user, groups=groups)
    return _require_object_list(groups, detail="permission_group_list_invalid_payload")


def _list_assignable_groups(ctx: AuthContextDep, service: PermissionGroupsService) -> list[dict]:
    if ctx.snapshot.is_admin:
        return _require_object_list(service.list_groups(), detail="permission_group_list_invalid_payload")
    _assert_group_management(ctx)
    groups = _list_manageable_groups(ctx, service)
    return [group for group in groups if group_tool_scope_within_snapshot(ctx.snapshot, group)]


def _get_manageable_group(ctx: AuthContextDep, service: PermissionGroupsService, group_id: int) -> dict:
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="permission_group_not_found")
    group = _require_object_payload(group, detail="permission_group_invalid_payload")
    group = service.assert_group_manageable(user=ctx.user, group=group)
    group = _require_object_payload(group, detail="permission_group_invalid_payload")
    try:
        group = ctx.deps.knowledge_management_manager.assert_permission_group_manageable(
            user=ctx.user,
            group=group,
        )
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc
    try:
        group = _chat_management_manager(ctx).assert_permission_group_manageable(
            user=ctx.user,
            group=group,
        )
        return _require_object_payload(group, detail="permission_group_invalid_payload")
    except Exception as exc:
        raise HTTPException(status_code=int(getattr(exc, "status_code", 403) or 403), detail=str(exc)) from exc


def _list_manageable_folder_snapshot(ctx: AuthContextDep, service: PermissionGroupsService) -> dict:
    groups = _list_manageable_groups(ctx, service)
    snapshot = _require_folder_snapshot(
        service.list_group_folders(),
        detail="permission_group_folder_snapshot_invalid_payload",
    )
    clean_user_id = str(getattr(ctx.user, "user_id", "") or "").strip()
    folders = list(snapshot.get("folders", []))
    by_id = {
        str(folder.get("id")): folder
        for folder in folders
        if isinstance(folder.get("id"), str) and folder.get("id")
    }
    visible_ids: set[str] = set()
    group_bindings: dict[str, str | None] = {}
    root_group_count = 0

    def _include_with_ancestors(folder_id: str | None) -> None:
        current_id = str(folder_id or "").strip()
        guard: set[str] = set()
        while current_id and current_id not in guard:
            guard.add(current_id)
            visible_ids.add(current_id)
            parent_id = by_id.get(current_id, {}).get("parent_id")
            current_id = str(parent_id).strip() if isinstance(parent_id, str) and parent_id.strip() else ""

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = group.get("group_id")
        if not isinstance(group_id, int):
            continue
        clean_folder_id = str(group.get("folder_id") or "").strip() or None
        group_bindings[str(group_id)] = clean_folder_id
        if clean_folder_id is None:
            root_group_count += 1
        _include_with_ancestors(clean_folder_id)
    for folder in folders:
        if str(folder.get("created_by") or "").strip() == clean_user_id:
            _include_with_ancestors(folder.get("id"))

    return {
        **snapshot,
        "folders": [folder for folder in folders if str(folder.get("id") or "") in visible_ids],
        "group_bindings": group_bindings,
        "root_group_count": root_group_count,
    }


def _visible_folder_ids(folder_snapshot: dict) -> set[str]:
    return {
        str(folder.get("id"))
        for folder in (folder_snapshot or {}).get("folders", [])
        if isinstance(folder, dict) and isinstance(folder.get("id"), str) and folder.get("id")
    }


def _wrap_groups(groups: list[dict]) -> dict[str, list[dict]]:
    return {"groups": groups}


def _wrap_group(group: dict) -> dict[str, dict]:
    return {"group": group}


def _wrap_result(message: str, **extra: object) -> dict[str, dict[str, object]]:
    result: dict[str, object] = {"message": message}
    result.update(extra)
    return {"result": result}


def _wrap_knowledge_bases(knowledge_bases: list[dict]) -> dict[str, list[dict]]:
    return {"knowledge_bases": knowledge_bases}


def _wrap_knowledge_tree(knowledge_tree: dict) -> dict[str, dict]:
    return {"knowledge_tree": knowledge_tree}


def _wrap_chats(chats: list[dict]) -> dict[str, list[dict]]:
    return {"chats": chats}


def _wrap_folder_snapshot(folder_snapshot: dict) -> dict[str, dict]:
    return {"folder_snapshot": folder_snapshot}


def _wrap_folder(folder: dict) -> dict[str, dict]:
    return {"folder": folder}


def _raise_resource_error(action: str, exc: Exception, *, default_detail: str) -> None:
    logger.error("Failed to %s: %s", action, exc, exc_info=True)
    status_code = int(getattr(exc, "status_code", 500) or 500)
    detail = str(exc).strip() or default_detail
    raise HTTPException(status_code=status_code, detail=detail) from exc


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/permission-groups", response_model=PermissionGroupListEnvelope)
    async def list_permission_groups(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        groups = _list_manageable_groups(ctx, service)
        return _wrap_groups(groups)

    @router.get("/permission-groups/assignable", response_model=PermissionGroupListEnvelope)
    async def list_assignable_permission_groups(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        groups = _list_assignable_groups(ctx, service)
        return _wrap_groups(groups)

    @router.get("/permission-groups/{group_id}", response_model=PermissionGroupEnvelope)
    async def get_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        group = _get_manageable_group(ctx, service, group_id)
        return _wrap_group(group)

    @router.post("/permission-groups", response_model=PermissionGroupCreateResultEnvelope)
    async def create_permission_group(
        data: PermissionGroupCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        payload = data.model_dump()
        payload["created_by"] = ctx.payload.sub
        _validate_group_scope(
            ctx,
            accessible_kbs=payload.get("accessible_kbs"),
            accessible_kb_nodes=payload.get("accessible_kb_nodes"),
            accessible_chats=payload.get("accessible_chats"),
        )
        group_id = service.create_group(payload)
        if type(group_id) is not int:
            raise HTTPException(status_code=502, detail="permission_group_create_invalid_payload")
        return _wrap_result("permission_group_created", group_id=group_id)

    @router.put("/permission-groups/{group_id}", response_model=ResultEnvelope)
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
            accessible_chats=merged.get("accessible_chats"),
        )
        success = service.update_group(group_id, payload)
        if not success:
            raise HTTPException(status_code=400, detail="permission_group_update_failed")
        return _wrap_result("permission_group_updated")

    @router.delete("/permission-groups/{group_id}", response_model=ResultEnvelope)
    async def delete_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        _get_manageable_group(ctx, service, group_id)
        success = service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=400, detail="permission_group_delete_failed")
        return _wrap_result("permission_group_deleted")

    @router.get("/permission-groups/resources/knowledge-bases", response_model=PermissionGroupKnowledgeBasesEnvelope)
    async def get_knowledge_bases(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            kb_list = ctx.deps.knowledge_management_manager.list_manageable_datasets(ctx.user)
            kb_list = _require_object_list(kb_list, detail="permission_group_knowledge_bases_invalid_payload")
            return _wrap_knowledge_bases(kb_list)
        except HTTPException:
            raise
        except Exception as exc:
            _raise_resource_error(
                "get permission group knowledge bases",
                exc,
                default_detail="permission_group_knowledge_bases_unavailable",
            )

    @router.get("/permission-groups/resources/knowledge-tree", response_model=PermissionGroupKnowledgeTreeEnvelope)
    async def get_knowledge_tree(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            tree_data = ctx.deps.knowledge_management_manager.list_visible_tree(ctx.user)
            tree_data = _require_knowledge_tree(tree_data, detail="permission_group_knowledge_tree_invalid_payload")
            return _wrap_knowledge_tree(tree_data)
        except HTTPException:
            raise
        except Exception as exc:
            _raise_resource_error(
                "get permission group knowledge tree",
                exc,
                default_detail="permission_group_knowledge_tree_unavailable",
            )

    @router.get("/permission-groups/resources/chats", response_model=PermissionGroupChatsEnvelope)
    async def get_chat_agents(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            chat_list = _chat_management_manager(ctx).list_manageable_chat_resources(ctx.user)
            chat_list = _require_object_list(chat_list, detail="permission_group_chats_invalid_payload")
            return _wrap_chats(chat_list)
        except HTTPException:
            raise
        except Exception as exc:
            _raise_resource_error(
                "get permission group chats",
                exc,
                default_detail="permission_group_chats_unavailable",
            )

    @router.get("/permission-groups/resources/group-folders", response_model=PermissionGroupFolderSnapshotEnvelope)
    async def get_group_folders(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        try:
            _assert_group_management(ctx)
            return _wrap_folder_snapshot(_list_manageable_folder_snapshot(ctx, service))
        except HTTPException:
            raise
        except Exception as exc:
            _raise_resource_error(
                "get permission group folders",
                exc,
                default_detail="permission_group_folders_unavailable",
            )

    @router.post("/permission-groups/folders", response_model=PermissionGroupFolderEnvelope)
    async def create_group_folder(
        data: PermissionGroupFolderCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        if data.parent_id:
            folder_snapshot = _list_manageable_folder_snapshot(ctx, service)
            if data.parent_id not in _visible_folder_ids(folder_snapshot):
                raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
        folder = service.create_group_folder(name=data.name, parent_id=data.parent_id, created_by=ctx.payload.sub)
        folder = _require_object_payload(folder, detail="permission_group_folder_invalid_payload")
        return _wrap_folder(folder)

    @router.put("/permission-groups/folders/{folder_id}", response_model=PermissionGroupFolderEnvelope)
    async def update_group_folder(
        folder_id: str,
        data: PermissionGroupFolderUpdate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        folder_snapshot = _list_manageable_folder_snapshot(ctx, service)
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
        folder = _require_object_payload(folder, detail="permission_group_folder_invalid_payload")
        return _wrap_folder(folder)

    @router.delete("/permission-groups/folders/{folder_id}", response_model=ResultEnvelope)
    async def delete_group_folder(
        folder_id: str,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        _assert_group_management(ctx)
        folder_snapshot = _list_manageable_folder_snapshot(ctx, service)
        if folder_id not in _visible_folder_ids(folder_snapshot):
            raise HTTPException(status_code=403, detail="permission_group_folder_out_of_management_scope")
        ok = service.delete_group_folder(folder_id)
        if not ok:
            raise HTTPException(status_code=404, detail="folder_not_found")
        return _wrap_result("permission_group_folder_deleted")

    return router
