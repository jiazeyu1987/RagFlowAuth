from __future__ import annotations

from fastapi import Depends

from backend.app.core.auth import get_deps
from backend.app.dependencies import AppDependencies
from backend.app.modules.permission_groups.service import PermissionGroupsService


def get_service(deps: AppDependencies = Depends(get_deps)) -> PermissionGroupsService:
    return PermissionGroupsService(deps)
