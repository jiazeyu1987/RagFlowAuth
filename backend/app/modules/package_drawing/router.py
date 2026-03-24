from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_tool_allowed
from backend.services.package_drawing import PackageDrawingImportError, PackageDrawingManager

router = APIRouter()


class PackageDrawingImportResult(BaseModel):
    filename: str = ""
    rows_scanned: int = 0
    total: int = 0
    success: int = 0
    failed: int = 0
    errors: list[dict] = Field(default_factory=list)


class PackageDrawingQueryResult(BaseModel):
    model: str
    barcode: str = ""
    parameters: dict[str, str] = Field(default_factory=dict)
    images: list[dict] = Field(default_factory=list)


@router.post("/package-drawing/import", response_model=PackageDrawingImportResult)
async def import_package_drawing_excel(ctx: AuthContextDep, file: UploadFile = File(...)):
    assert_tool_allowed(ctx.snapshot, "package_drawing")
    if not ctx.snapshot.is_admin:
        raise HTTPException(status_code=403, detail="admin_required")
    manager = PackageDrawingManager(ctx.deps)
    try:
        return await manager.import_from_upload(file)
    except PackageDrawingImportError as exc:
        code = str(exc.code or "").strip()
        status_code = 500 if code.startswith("excel_engine_unavailable") else 400
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.get("/package-drawing/by-model", response_model=PackageDrawingQueryResult)
async def query_package_drawing_by_model(
    ctx: AuthContextDep,
    model: str = Query(..., min_length=1, max_length=256),
):
    assert_tool_allowed(ctx.snapshot, "package_drawing")
    manager = PackageDrawingManager(ctx.deps)
    payload = manager.query_by_model(model)
    if payload is None:
        raise HTTPException(status_code=404, detail="model_not_found")
    return payload


@router.get("/package-drawing/images/{image_id}")
async def get_package_drawing_image(image_id: str, ctx: AuthContextDep):
    assert_tool_allowed(ctx.snapshot, "package_drawing")
    manager = PackageDrawingManager(ctx.deps)
    payload = manager.get_image_binary(image_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="image_not_found")
    content, filename, mime_type = payload
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
