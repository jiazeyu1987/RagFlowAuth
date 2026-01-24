from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import get_deps
from backend.app.core.authz import AdminOnly
from backend.app.dependencies import AppDependencies
from backend.models.org_directory import (
    OrgDirectoryAuditLogResponse,
    OrgDirectoryCreateRequest,
    OrgDirectoryItem,
    OrgDirectoryUpdateRequest,
)


router = APIRouter()


def _deps(deps: AppDependencies = Depends(get_deps)) -> AppDependencies:
    return deps


@router.get("/org/companies", response_model=list[OrgDirectoryItem])
async def list_companies(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    companies = deps.org_directory_store.list_companies()
    return [
        OrgDirectoryItem(id=c.company_id, name=c.name, created_at_ms=c.created_at_ms, updated_at_ms=c.updated_at_ms)
        for c in companies
    ]


@router.post("/org/companies", response_model=OrgDirectoryItem, status_code=201)
async def create_company(payload: AdminOnly, body: OrgDirectoryCreateRequest, deps: AppDependencies = Depends(_deps)):
    try:
        c = deps.org_directory_store.create_company(name=body.name, actor_user_id=payload.sub)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Likely unique constraint
        raise HTTPException(status_code=400, detail=str(e))
    return OrgDirectoryItem(id=c.company_id, name=c.name, created_at_ms=c.created_at_ms, updated_at_ms=c.updated_at_ms)


@router.put("/org/companies/{company_id}", response_model=OrgDirectoryItem)
async def update_company(
    company_id: int,
    payload: AdminOnly,
    body: OrgDirectoryUpdateRequest,
    deps: AppDependencies = Depends(_deps),
):
    try:
        c = deps.org_directory_store.update_company(company_id=company_id, name=body.name, actor_user_id=payload.sub)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OrgDirectoryItem(id=c.company_id, name=c.name, created_at_ms=c.created_at_ms, updated_at_ms=c.updated_at_ms)


@router.delete("/org/companies/{company_id}")
async def delete_company(company_id: int, payload: AdminOnly, deps: AppDependencies = Depends(_deps)):
    try:
        deps.org_directory_store.delete_company(company_id=company_id, actor_user_id=payload.sub)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/org/departments", response_model=list[OrgDirectoryItem])
async def list_departments(_: AdminOnly, deps: AppDependencies = Depends(_deps)):
    depts = deps.org_directory_store.list_departments()
    return [
        OrgDirectoryItem(id=d.department_id, name=d.name, created_at_ms=d.created_at_ms, updated_at_ms=d.updated_at_ms)
        for d in depts
    ]


@router.post("/org/departments", response_model=OrgDirectoryItem, status_code=201)
async def create_department(payload: AdminOnly, body: OrgDirectoryCreateRequest, deps: AppDependencies = Depends(_deps)):
    try:
        d = deps.org_directory_store.create_department(name=body.name, actor_user_id=payload.sub)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OrgDirectoryItem(id=d.department_id, name=d.name, created_at_ms=d.created_at_ms, updated_at_ms=d.updated_at_ms)


@router.put("/org/departments/{department_id}", response_model=OrgDirectoryItem)
async def update_department(
    department_id: int,
    payload: AdminOnly,
    body: OrgDirectoryUpdateRequest,
    deps: AppDependencies = Depends(_deps),
):
    try:
        d = deps.org_directory_store.update_department(
            department_id=department_id, name=body.name, actor_user_id=payload.sub
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OrgDirectoryItem(id=d.department_id, name=d.name, created_at_ms=d.created_at_ms, updated_at_ms=d.updated_at_ms)


@router.delete("/org/departments/{department_id}")
async def delete_department(department_id: int, payload: AdminOnly, deps: AppDependencies = Depends(_deps)):
    try:
        deps.org_directory_store.delete_department(department_id=department_id, actor_user_id=payload.sub)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/org/audit", response_model=list[OrgDirectoryAuditLogResponse])
async def list_org_audit_logs(
    _: AdminOnly,
    deps: AppDependencies = Depends(_deps),
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 200,
):
    logs = deps.org_directory_store.list_audit_logs(entity_type=entity_type, action=action, limit=limit)
    user_ids = {l.actor_user_id for l in logs if l.actor_user_id}
    usernames = {}
    try:
        usernames = deps.user_store.get_usernames_by_ids(user_ids)
    except Exception:
        usernames = {}

    return [
        OrgDirectoryAuditLogResponse(
            id=l.id,
            entity_type=l.entity_type,
            action=l.action,
            entity_id=l.entity_id,
            before_name=l.before_name,
            after_name=l.after_name,
            actor_user_id=l.actor_user_id,
            actor_username=usernames.get(l.actor_user_id),
            created_at_ms=l.created_at_ms,
        )
        for l in logs
    ]

