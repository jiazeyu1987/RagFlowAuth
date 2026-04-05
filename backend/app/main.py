from __future__ import annotations

import logging
from contextlib import asynccontextmanager
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.errors import register_exception_handlers
from backend.app.core.request_id import RequestIdMiddleware
from backend.core.security import auth as authx_auth

logger = logging.getLogger(__name__)


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

    from backend.app.modules.admin_notifications.router import router as admin_notifications_router
    from backend.app.modules.agents.router import router as agents_router
    from backend.app.modules.audit.router import router as audit_router
    from backend.app.modules.auth.router import router as auth_router
    from backend.app.modules.chat.router import router as chat_router
    from backend.app.modules.data_security.router import router as data_security_router
    from backend.app.modules.diagnostics.router import router as diagnostics_router
    from backend.app.modules.documents.router import router as documents_router
    from backend.app.modules.drug_admin.router import router as drug_admin_router
    from backend.app.modules.electronic_signature.router import router as electronic_signature_router
    from backend.app.modules.emergency_changes.router import router as emergency_changes_router
    from backend.app.modules.inbox.router import router as inbox_router
    from backend.app.modules.knowledge.router import router as knowledge_router
    from backend.app.modules.me.router import router as me_router
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

    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(electronic_signature_router, prefix="/api", tags=["Electronic Signature"])
    app.include_router(audit_router, prefix="/api", tags=["Audit"])
    app.include_router(admin_notifications_router, prefix="/api", tags=["Admin Notifications"])
    app.include_router(emergency_changes_router, prefix="/api", tags=["Emergency Changes"])
    app.include_router(supplier_qualification_router, prefix="/api", tags=["Supplier Qualification"])
    app.include_router(training_compliance_router, prefix="/api", tags=["Training Compliance"])
    app.include_router(users_router, prefix="/api/users", tags=["Users"])
    app.include_router(knowledge_router, prefix="/api/knowledge", tags=["Knowledge Base"])
    app.include_router(operation_approvals_router, prefix="/api", tags=["Operation Approvals"])
    app.include_router(inbox_router, prefix="/api", tags=["Inbox"])
    app.include_router(ragflow_router, prefix="/api/ragflow", tags=["RAGFlow Integration"])
    app.include_router(preview_router, prefix="/api", tags=["Preview Gateway"])
    app.include_router(documents_router, prefix="/api", tags=["Documents"])
    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(agents_router, prefix="/api", tags=["Agents"])
    app.include_router(search_configs_router, prefix="/api", tags=["Search Configs"])
    app.include_router(me_router, prefix="/api", tags=["Me"])
    app.include_router(nas_router, prefix="/api", tags=["NAS"])
    app.include_router(onlyoffice_router, prefix="/api", tags=["ONLYOFFICE"])
    app.include_router(data_security_router, prefix="/api", tags=["Data Security"])
    app.include_router(create_permission_groups_router(), prefix="/api", tags=["Permission Groups"])
    app.include_router(org_directory_router, prefix="/api", tags=["Org Directory"])
    app.include_router(patent_download_router, prefix="/api", tags=["Patent Download"])
    app.include_router(paper_download_router, prefix="/api", tags=["Paper Download"])
    app.include_router(package_drawing_router, prefix="/api", tags=["Package Drawing"])
    app.include_router(drug_admin_router, prefix="/api", tags=["Drug Admin"])
    app.include_router(diagnostics_router, prefix="/api", tags=["Diagnostics"])

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
