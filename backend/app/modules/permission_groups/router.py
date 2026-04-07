from __future__ import annotations

from fastapi import APIRouter

from backend.app.modules.permission_groups.dependencies import get_service
from backend.app.modules.permission_groups.folder_routes import register_folder_routes
from backend.app.modules.permission_groups.group_routes import register_group_routes
from backend.app.modules.permission_groups.resource_routes import register_resource_routes


def create_router() -> APIRouter:
    router = APIRouter()
    register_group_routes(router)
    register_resource_routes(router)
    register_folder_routes(router)
    return router
