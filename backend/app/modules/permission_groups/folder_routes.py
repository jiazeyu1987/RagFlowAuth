from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.authz import AuthContextDep
from backend.app.modules.permission_groups.dependencies import get_service
from backend.app.modules.permission_groups import folders as permission_folders
from backend.app.modules.permission_groups.schemas import (
    PermissionGroupFolderCreate,
    PermissionGroupFolderUpdate,
)
from backend.app.modules.permission_groups.service import PermissionGroupsService
from backend.models.auth import ResultEnvelope
from backend.models.permission_group import (
    PermissionGroupFolderEnvelope,
    PermissionGroupFolderSnapshotEnvelope,
)


def register_folder_routes(router: APIRouter) -> None:
    @router.get("/permission-groups/resources/group-folders", response_model=PermissionGroupFolderSnapshotEnvelope)
    def get_group_folders(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_folders.folder_snapshot_result(ctx, service)

    @router.post("/permission-groups/folders", response_model=PermissionGroupFolderEnvelope)
    def create_group_folder(
        data: PermissionGroupFolderCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_folders.create_group_folder_result(ctx, service, data)

    @router.put("/permission-groups/folders/{folder_id}", response_model=PermissionGroupFolderEnvelope)
    def update_group_folder(
        folder_id: str,
        data: PermissionGroupFolderUpdate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_folders.update_group_folder_result(ctx, service, folder_id, data)

    @router.delete("/permission-groups/folders/{folder_id}", response_model=ResultEnvelope)
    def delete_group_folder(
        folder_id: str,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_folders.delete_group_folder_result(ctx, service, folder_id)
