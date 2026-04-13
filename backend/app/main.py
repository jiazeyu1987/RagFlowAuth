from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings, validate_jwt_secret
from backend.app.core.errors import register_exception_handlers
from backend.app.core.request_id import RequestIdMiddleware
from backend.core.security import auth as authx_auth

logger = logging.getLogger(__name__)

RouterFactory = Callable[[], APIRouter]


@dataclass(frozen=True)
class RouterRegistrationSpec:
    prefix: str
    tags: tuple[str, ...]
    router: APIRouter | None = None
    router_factory: RouterFactory | None = None

    def resolve_router(self) -> APIRouter:
        if self.router_factory is not None:
            return self.router_factory()
        if self.router is None:
            raise RuntimeError("router_registration_spec_missing_target")
        return self.router


@lru_cache(maxsize=1)
def _build_router_registration_specs() -> tuple[RouterRegistrationSpec, ...]:
    from backend.app.modules.admin_notifications.router import router as admin_notifications_router
    from backend.app.modules.agents.router import router as agents_router
    from backend.app.modules.audit.router import router as audit_router
    from backend.app.modules.auth.router import router as auth_router
    from backend.app.modules.chat.router import router as chat_router
    from backend.app.modules.change_control.router import router as change_control_router
    from backend.app.modules.data_security.router import router as data_security_router
    from backend.app.modules.diagnostics.router import router as diagnostics_router
    from backend.app.modules.document_control.router import router as document_control_router
    from backend.app.modules.documents.router import router as documents_router
    from backend.app.modules.drug_admin.router import router as drug_admin_router
    from backend.app.modules.electronic_signature.router import router as electronic_signature_router
    from backend.app.modules.emergency_changes.router import router as emergency_changes_router
    from backend.app.modules.equipment.router import router as equipment_router
    from backend.app.modules.inbox.router import router as inbox_router
    from backend.app.modules.knowledge.router import router as knowledge_router
    from backend.app.modules.maintenance.router import router as maintenance_router
    from backend.app.modules.me.router import router as me_router
    from backend.app.modules.metrology.router import router as metrology_router
    from backend.app.modules.nas.router import router as nas_router
    from backend.app.modules.onlyoffice.router import router as onlyoffice_router
    from backend.app.modules.operation_approvals.router import router as operation_approvals_router
    from backend.app.modules.org_directory.router import router as org_directory_router
    from backend.app.modules.package_drawing.router import router as package_drawing_router
    from backend.app.modules.paper_download.router import router as paper_download_router
    from backend.app.modules.patent_download.router import router as patent_download_router
    from backend.app.modules.permission_groups.router import create_router as create_permission_groups_router
    from backend.app.modules.preview.router import router as preview_router
    from backend.app.modules.ragflow.router import router as ragflow_router
    from backend.app.modules.search_configs.router import router as search_configs_router
    from backend.app.modules.supplier_qualification.router import router as supplier_qualification_router
    from backend.app.modules.training_compliance.router import router as training_compliance_router
    from backend.app.modules.users.router import router as users_router

    return (
        RouterRegistrationSpec(prefix="/api/auth", tags=("Authentication",), router=auth_router),
        RouterRegistrationSpec(prefix="/api", tags=("Electronic Signature",), router=electronic_signature_router),
        RouterRegistrationSpec(prefix="/api", tags=("Audit",), router=audit_router),
        RouterRegistrationSpec(prefix="/api", tags=("Admin Notifications",), router=admin_notifications_router),
        RouterRegistrationSpec(prefix="/api", tags=("Emergency Changes",), router=emergency_changes_router),
        RouterRegistrationSpec(prefix="/api", tags=("Change Control",), router=change_control_router),
        RouterRegistrationSpec(prefix="/api", tags=("Equipment",), router=equipment_router),
        RouterRegistrationSpec(prefix="/api", tags=("Metrology",), router=metrology_router),
        RouterRegistrationSpec(prefix="/api", tags=("Maintenance",), router=maintenance_router),
        RouterRegistrationSpec(prefix="/api", tags=("Supplier Qualification",), router=supplier_qualification_router),
        RouterRegistrationSpec(prefix="/api", tags=("Training Compliance",), router=training_compliance_router),
        RouterRegistrationSpec(prefix="/api/users", tags=("Users",), router=users_router),
        RouterRegistrationSpec(prefix="/api/knowledge", tags=("Knowledge Base",), router=knowledge_router),
        RouterRegistrationSpec(prefix="/api", tags=("Operation Approvals",), router=operation_approvals_router),
        RouterRegistrationSpec(prefix="/api", tags=("Inbox",), router=inbox_router),
        RouterRegistrationSpec(prefix="/api", tags=("Document Control",), router=document_control_router),
        RouterRegistrationSpec(prefix="/api/ragflow", tags=("RAGFlow Integration",), router=ragflow_router),
        RouterRegistrationSpec(prefix="/api", tags=("Preview Gateway",), router=preview_router),
        RouterRegistrationSpec(prefix="/api", tags=("Documents",), router=documents_router),
        RouterRegistrationSpec(prefix="/api", tags=("Chat",), router=chat_router),
        RouterRegistrationSpec(prefix="/api", tags=("Agents",), router=agents_router),
        RouterRegistrationSpec(prefix="/api", tags=("Search Configs",), router=search_configs_router),
        RouterRegistrationSpec(prefix="/api", tags=("Me",), router=me_router),
        RouterRegistrationSpec(prefix="/api", tags=("NAS",), router=nas_router),
        RouterRegistrationSpec(prefix="/api", tags=("ONLYOFFICE",), router=onlyoffice_router),
        RouterRegistrationSpec(prefix="/api", tags=("Data Security",), router=data_security_router),
        RouterRegistrationSpec(
            prefix="/api",
            tags=("Permission Groups",),
            router_factory=create_permission_groups_router,
        ),
        RouterRegistrationSpec(prefix="/api", tags=("Org Directory",), router=org_directory_router),
        RouterRegistrationSpec(prefix="/api", tags=("Patent Download",), router=patent_download_router),
        RouterRegistrationSpec(prefix="/api", tags=("Paper Download",), router=paper_download_router),
        RouterRegistrationSpec(prefix="/api", tags=("Package Drawing",), router=package_drawing_router),
        RouterRegistrationSpec(prefix="/api", tags=("Drug Admin",), router=drug_admin_router),
        RouterRegistrationSpec(prefix="/api", tags=("Diagnostics",), router=diagnostics_router),
    )


def _register_application_routers(app: FastAPI) -> None:
    for spec in _build_router_registration_specs():
        app.include_router(spec.resolve_router(), prefix=spec.prefix, tags=list(spec.tags))


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.dependencies import initialize_application_dependencies
    from backend.services.data_security_scheduler_v2 import init_scheduler_v2, stop_scheduler_v2

    initialize_application_dependencies(app)
    logger.info("Dependencies initialized")

    # Help diagnose stale code / wrong interpreter issues on Windows.
    try:
        import backend.services.ragflow_chat_service as rcs

        service_path = Path(getattr(rcs, "__file__", "") or "")
        modified_ns = None
        try:
            if service_path and service_path.exists():
                stat = service_path.stat()
                modified_ns = getattr(stat, "st_mtime_ns", None) or int(stat.st_mtime * 1_000_000_000)
        except Exception:
            modified_ns = None
        logging.getLogger("uvicorn.error").warning(
            "Runtime python=%s ragflow_chat_service=%s mtime_ns=%s",
            sys.executable,
            str(service_path) if service_path else "(unknown)",
            str(modified_ns) if modified_ns is not None else "(unknown)",
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
    except Exception as exc:
        logger.error(f"Failed to start improved backup scheduler V2: {exc}", exc_info=True)
        raise

    yield

    try:
        if settings.BACKUP_SCHEDULER_ENABLED:
            stop_scheduler_v2()
            logger.info("Backup scheduler V2 stopped")
    except Exception as exc:
        logger.error(f"Error stopping scheduler V2: {exc}", exc_info=True)

    logger.info("Shutting down...")


def create_app() -> FastAPI:
    validate_jwt_secret(settings)
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
