from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.core.authz import AuthContextDep
from backend.services.nas_browser_service import NasBrowserService

router = APIRouter()


class NasListResponse(BaseModel):
    current_path: str = ""
    parent_path: str | None = None
    root_path: str = ""
    items: list[dict] = Field(default_factory=list)


class NasImportRequest(BaseModel):
    path: str = ""
    kb_ref: str = ""


@router.get("/nas/files", response_model=NasListResponse)
async def list_nas_files(
    ctx: AuthContextDep,
    path: str = Query("", description="NAS 相对路径，根目录为空字符串"),
):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    return await NasBrowserService().list_directory(path or "")


@router.post("/nas/import-folder")
async def start_nas_folder_import(
    body: NasImportRequest,
    ctx: AuthContextDep,
):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    return await NasBrowserService().start_folder_import_task(
        relative_path=body.path or "",
        kb_ref=body.kb_ref or "",
        deps=ctx.deps,
        ctx=ctx,
    )


@router.get("/nas/import-folder/{task_id}")
async def get_nas_folder_import_status(
    task_id: str,
    ctx: AuthContextDep,
):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    try:
        return await NasBrowserService().get_folder_import_task(task_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/nas/import-file")
async def import_nas_file_to_kb(
    body: NasImportRequest,
    ctx: AuthContextDep,
):
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")

    return await NasBrowserService().import_file_to_kb(
        relative_path=body.path or "",
        kb_ref=body.kb_ref or "",
        deps=ctx.deps,
        ctx=ctx,
    )
