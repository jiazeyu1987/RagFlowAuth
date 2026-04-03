from __future__ import annotations

import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.core.auth import get_global_deps
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies
from backend.database.tenant_paths import resolve_tenant_auth_db_path
from backend.models.org_directory import (
    OrgCompanyItem,
    OrgDepartmentItem,
    OrgDirectoryAuditLogResponse,
    OrgDirectoryCreateRequest,
    OrgDirectoryUpdateRequest,
    OrgStructureRebuildResponse,
    OrgTreeNode,
)


router = APIRouter()
logger = logging.getLogger(__name__)
SUPPORTED_EXCEL_SUFFIXES = {".xls", ".xlsx"}


def _deps(deps: AppDependencies = Depends(get_global_deps)) -> AppDependencies:
    return deps


def _managed_by_excel_conflict() -> HTTPException:
    return HTTPException(status_code=409, detail="org_structure_managed_by_excel")


def _company_item(company) -> OrgCompanyItem:
    tenant_db_path = str(resolve_tenant_auth_db_path(company.company_id))
    return OrgCompanyItem(
        id=company.company_id,
        name=company.name,
        source_key=company.source_key,
        created_at_ms=company.created_at_ms,
        updated_at_ms=company.updated_at_ms,
        tenant_db_path=tenant_db_path,
    )


def _department_item(department) -> OrgDepartmentItem:
    return OrgDepartmentItem(
        id=department.department_id,
        name=department.name,
        path_name=department.path_name,
        company_id=department.company_id,
        parent_department_id=department.parent_department_id,
        source_key=department.source_key,
        source_department_id=department.source_department_id,
        level_no=department.level_no,
        sort_order=department.sort_order,
        created_at_ms=department.created_at_ms,
        updated_at_ms=department.updated_at_ms,
    )


@router.get("/org/tree", response_model=list[OrgTreeNode])
async def get_org_tree(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    return deps.org_structure_manager.get_tree()


@router.post("/org/rebuild-from-excel", response_model=OrgStructureRebuildResponse)
async def rebuild_from_excel(
    payload: AdminOnly,
    excel_file: UploadFile = File(...),
    deps: AppDependencies = Depends(_deps),
):
    filename = Path(str(excel_file.filename or "").strip()).name
    if not filename:
        raise HTTPException(status_code=400, detail="org_structure_excel_filename_required")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXCEL_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"org_structure_excel_extension_invalid:{suffix or filename}")

    temp_file_path: str | None = None
    try:
        content = await excel_file.read()
        if not content:
            raise HTTPException(status_code=400, detail="org_structure_excel_empty")
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        summary = deps.org_structure_manager.rebuild_from_excel(
            actor_user_id=payload.sub,
            excel_path=temp_file_path,
            source_label=filename,
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.warning("Failed to rebuild org structure from uploaded Excel %s: %s", filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to rebuild org structure from Excel: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await excel_file.close()
        if temp_file_path:
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to clean temp org Excel file: %s", temp_file_path)
    return OrgStructureRebuildResponse.model_validate(summary.__dict__)


@router.get("/org/companies", response_model=list[OrgCompanyItem])
async def list_companies(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    companies = deps.org_structure_manager.list_companies()
    return [_company_item(item) for item in companies]


@router.post("/org/companies", response_model=OrgCompanyItem, status_code=201)
async def create_company(
    payload: AdminOnly,
    body: OrgDirectoryCreateRequest,
    deps: AppDependencies = Depends(_deps),
):
    del payload, body, deps
    raise _managed_by_excel_conflict()


@router.put("/org/companies/{company_id}", response_model=OrgCompanyItem)
async def update_company(
    company_id: int,
    payload: AdminOnly,
    body: OrgDirectoryUpdateRequest,
    deps: AppDependencies = Depends(_deps),
):
    del company_id, payload, body, deps
    raise _managed_by_excel_conflict()


@router.delete("/org/companies/{company_id}")
async def delete_company(company_id: int, payload: AdminOnly, deps: AppDependencies = Depends(_deps)):
    del company_id, payload, deps
    raise _managed_by_excel_conflict()


@router.get("/org/departments", response_model=list[OrgDepartmentItem])
async def list_departments(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    departments = deps.org_structure_manager.list_departments_flat()
    return [_department_item(item) for item in departments]


@router.post("/org/departments", response_model=OrgDepartmentItem, status_code=201)
async def create_department(
    payload: AdminOnly,
    body: OrgDirectoryCreateRequest,
    deps: AppDependencies = Depends(_deps),
):
    del payload, body, deps
    raise _managed_by_excel_conflict()


@router.put("/org/departments/{department_id}", response_model=OrgDepartmentItem)
async def update_department(
    department_id: int,
    payload: AdminOnly,
    body: OrgDirectoryUpdateRequest,
    deps: AppDependencies = Depends(_deps),
):
    del department_id, payload, body, deps
    raise _managed_by_excel_conflict()


@router.delete("/org/departments/{department_id}")
async def delete_department(department_id: int, payload: AdminOnly, deps: AppDependencies = Depends(_deps)):
    del department_id, payload, deps
    raise _managed_by_excel_conflict()


@router.get("/org/audit", response_model=list[OrgDirectoryAuditLogResponse])
async def list_org_audit_logs(
    _: AdminOnly,
    deps: AppDependencies = Depends(_deps),
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 200,
):
    try:
        logs = deps.org_structure_manager.list_audit_logs(entity_type=entity_type, action=action, limit=limit)
    except Exception as exc:
        logger.exception("Failed to list org audit logs: %s", exc)
        logs = []
    user_ids = {item.actor_user_id for item in logs if item.actor_user_id}
    usernames = {}
    try:
        usernames = deps.user_store.get_usernames_by_ids(user_ids)
    except Exception:
        usernames = {}

    return [
        OrgDirectoryAuditLogResponse(
            id=item.id,
            entity_type=item.entity_type,
            action=item.action,
            entity_id=item.entity_id,
            before_name=item.before_name,
            after_name=item.after_name,
            actor_user_id=item.actor_user_id,
            actor_username=usernames.get(item.actor_user_id),
            created_at_ms=item.created_at_ms,
        )
        for item in logs
    ]
