from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.request_id import RequestIdMiddleware
from backend.core.security import auth as authx_auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.dependencies import create_dependencies
    from backend.app.modules.data_security.scheduler import start_data_security_scheduler

    app.state.deps = create_dependencies()
    logger.info("Dependencies initialized")

    stop_event = threading.Event()
    app.state.data_security_scheduler_stop = stop_event
    app.state.data_security_scheduler_thread = start_data_security_scheduler(stop_event=stop_event)

    yield
    stop_event.set()
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Knowledge base authentication and authorization service",
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    authx_auth.handle_errors(app)

    from backend.api import (
        agents,
        auth,
        chat,
        data_security,
        diagnostics,
        knowledge,
        me,
        permission_groups,
        ragflow,
        review,
        users,
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
    app.include_router(review.router, prefix="/api/knowledge", tags=["Document Review"])
    app.include_router(ragflow.router, prefix="/api/ragflow", tags=["RAGFlow Integration"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(agents.router, prefix="/api", tags=["Agents"])
    app.include_router(me.router, prefix="/api", tags=["Me"])
    app.include_router(data_security.router, prefix="/api", tags=["Data Security"])
    app.include_router(permission_groups.create_router(), prefix="/api", tags=["Permission Groups"])
    app.include_router(diagnostics.router, prefix="/api", tags=["Diagnostics"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "auth-backend-fastapi"}

    @app.get("/")
    async def root():
        return {
            "service": "Auth Backend (FastAPI)",
            "version": settings.APP_VERSION,
            "auth": "AuthX JWT",
        }

    return app


app = create_app()
