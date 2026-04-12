from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.authz import AuthContextDep
from backend.app.modules.permission_groups.dependencies import get_service
from backend.app.modules.permission_groups import mutations as permission_mutations
from backend.app.modules.permission_groups import queries as permission_queries
from backend.app.modules.permission_groups.schemas import (
    PermissionGroupCreate,
    PermissionGroupUpdate,
)
from backend.app.modules.permission_groups.service import PermissionGroupsService
from backend.models.auth import ResultEnvelope
from backend.models.permission_group import (
    PermissionGroupCreateResultEnvelope,
    PermissionGroupEnvelope,
    PermissionGroupListEnvelope,
)


def register_group_routes(router: APIRouter) -> None:
    @router.get("/permission-groups", response_model=PermissionGroupListEnvelope)
    def list_permission_groups(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_queries.list_permission_groups_result(ctx, service)

    @router.get("/permission-groups/assignable", response_model=PermissionGroupListEnvelope)
    def list_assignable_permission_groups(
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_queries.list_assignable_permission_groups_result(ctx, service)

    @router.get("/permission-groups/{group_id}", response_model=PermissionGroupEnvelope)
    def get_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_queries.get_permission_group_result(ctx, service, group_id)

    @router.post("/permission-groups", response_model=PermissionGroupCreateResultEnvelope)
    def create_permission_group(
        data: PermissionGroupCreate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_mutations.create_permission_group_result(ctx, service, data)

    @router.put("/permission-groups/{group_id}", response_model=ResultEnvelope)
    def update_permission_group(
        group_id: int,
        data: PermissionGroupUpdate,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_mutations.update_permission_group_result(ctx, service, group_id, data)

    @router.delete("/permission-groups/{group_id}", response_model=ResultEnvelope)
    def delete_permission_group(
        group_id: int,
        ctx: AuthContextDep,
        service: PermissionGroupsService = Depends(get_service),
    ):
        return permission_mutations.delete_permission_group_result(ctx, service, group_id)
