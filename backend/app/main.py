from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib import import_module
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.request_id import RequestIdMiddleware
from backend.core.security import auth as authx_auth

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouterRegistrationSpec:
    module_path: str
    prefix: str
    tags: tuple[str, ...]
    router_attr: str = "router"
    factory_attr: str | None = None


ROUTER_REGISTRATION_SPECS: tuple[RouterRegistrationSpec, ...] = (
    RouterRegistrationSpec("backend.app.modules.auth.router", "/api/auth", ("Authentication",)),
    RouterRegistrationSpec("backend.app.modules.electronic_signature.router", "/api", ("Electronic Signature",)),
    RouterRegistrationSpec("backend.app.modules.audit.router", "/api", ("Audit",)),
    RouterRegistrationSpec("backend.app.modules.admin_notifications.router", "/api", ("Admin Notifications",)),
    RouterRegistrationSpec("backend.app.modules.emergency_changes.router", "/api", ("Emergency Changes",)),
    RouterRegistrationSpec("backend.app.modules.supplier_qualification.router", "/api", ("Supplier Qualification",)),
    RouterRegistrationSpec("backend.app.modules.training_compliance.router", "/api", ("Training Compliance",)),
    RouterRegistrationSpec("backend.app.modules.users.router", "/api/users", ("Users",)),
    RouterRegistrationSpec("backend.app.modules.knowledge.router", "/api/knowledge", ("Knowledge Base",)),
    RouterRegistrationSpec("backend.app.modules.operation_approvals.router", "/api", ("Operation Approvals",)),
    RouterRegistrationSpec("backend.app.modules.inbox.router", "/api", ("Inbox",)),
    RouterRegistrationSpec("backend.app.modules.ragflow.router", "/api/ragflow", ("RAGFlow Integration",)),
    RouterRegistrationSpec("backend.app.modules.preview.router", "/api", ("Preview Gateway",)),
    RouterRegistrationSpec("backend.app.modules.documents.router", "/api", ("Documents",)),
    RouterRegistrationSpec("backend.app.modules.chat.router", "/api", ("Chat",)),
    RouterRegistrationSpec("backend.app.modules.agents.router", "/api", ("Agents",)),
    RouterRegistrationSpec("backend.app.modules.search_configs.router", "/api", ("Search Configs",)),
    RouterRegistrationSpec("backend.app.modules.me.router", "/api", ("Me",)),
    RouterRegistrationSpec("backend.app.modules.nas.router", "/api", ("NAS",)),
    RouterRegistrationSpec("backend.app.modules.onlyoffice.router", "/api", ("ONLYOFFICE",)),
    RouterRegistrationSpec("backend.app.modules.data_security.router", "/api", ("Data Security",)),
    RouterRegistrationSpec(
        "backend.app.modules.permission_groups.router",
        "/api",
        ("Permission Groups",),
        factory_attr="create_router",
    ),
    RouterRegistrationSpec("backend.app.modules.org_directory.router", "/api", ("Org Directory",)),
    RouterRegistrationSpec("backend.app.modules.patent_download.router", "/api", ("Patent Download",)),
    RouterRegistrationSpec("backend.app.modules.paper_download.router", "/api", ("Paper Download",)),
    RouterRegistrationSpec("backend.app.modules.package_drawing.router", "/api", ("Package Drawing",)),
    RouterRegistrationSpec("backend.app.modules.drug_admin.router", "/api", ("Drug Admin",)),
    RouterRegistrationSpec("backend.app.modules.diagnostics.router", "/api", ("Diagnostics",)),
)


def _resolve_router(spec: RouterRegistrationSpec) -> APIRouter:
    module = import_module(spec.module_path)
    if spec.factory_attr:
        router_factory = getattr(module, spec.factory_attr)
        return router_factory()
    return getattr(module, spec.router_attr)


def _register_application_routers(app: FastAPI) -> None:
    for spec in ROUTER_REGISTRATION_SPECS:
        app.include_router(_resolve_router(spec), prefix=spec.prefix, tags=list(spec.tags))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.dependencies import create_dependencies, get_tenant_dependencies
    from backend.database.paths import resolve_auth_db_path
    from backend.services.data_security_scheduler_v2 import init_scheduler_v2, stop_scheduler_v2

    app.state.base_auth_db_path = str(resolve_auth_db_path())
    app.state.tenant_deps_cache = {}
    app.state.deps = create_dependencies(
        operation_approval_execution_deps_resolver=lambda company_id: get_tenant_dependencies(
            app, company_id=company_id
        )
    )
    logger.info("Dependencies initialized")

    # Help diagnose "stale code" / wrong interpreter issues on Windows.
    try:
        import backend.services.ragflow_chat_service as rcs

        p = Path(getattr(rcs, "__file__", "") or "")
        m = None
        try:
            if p and p.exists():
                m = getattr(p.stat(), "st_mtime_ns", None) or int(p.stat().st_mtime * 1_000_000_000)
        except Exception:
            m = None
        logging.getLogger("uvicorn.error").warning(
            "Runtime python=%s ragflow_chat_service=%s mtime_ns=%s",
            sys.executable,
            str(p) if p else "(unknown)",
            str(m) if m is not None else "(unknown)",
        )
    except Exception:
        pass

    try:
        if settings.BACKUP_SCHEDULER_ENABLED:
            deps = app.state.deps
            scheduler = init_scheduler_v2(store=deps.data_security_store)
            scheduler.start()
            logger.info("Backup scheduler V2 started")
        else:
            logger.info("Backup scheduler V2 disabled by BACKUP_SCHEDULER_ENABLED=false")
    except Exception as e:
        logger.error(f"Failed to start improved backup scheduler V2: {e}", exc_info=True)
        raise

    yield
    try:
        if settings.BACKUP_SCHEDULER_ENABLED:
            stop_scheduler_v2()
            logger.info("Backup scheduler V2 stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler V2: {e}", exc_info=True)

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
    _register_application_routers(app)

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
