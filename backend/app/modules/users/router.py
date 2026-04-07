from __future__ import annotations

from fastapi import APIRouter

from backend.app.modules.users.dependencies import get_service as get_service
from backend.app.modules.users.password_routes import register_password_routes
from backend.app.modules.users.read_routes import register_read_routes
from backend.app.modules.users.write_routes import register_write_routes

USER_ROUTE_REGISTRARS = (
    register_read_routes,
    register_write_routes,
    register_password_routes,
)

def create_router(*, registrars=USER_ROUTE_REGISTRARS) -> APIRouter:
    router = APIRouter()
    for register_routes in registrars:
        register_routes(router)
    return router


router = create_router()

__all__ = [
    "USER_ROUTE_REGISTRARS",
    "create_router",
    "get_service",
    "router",
]
