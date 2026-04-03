from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from backend.app.core.authz import AuthContextDep
from backend.models.operation_approval import OperationApprovalRequestBrief
from backend.services.documents.document_manager import DocumentManager

router = APIRouter()


@router.get("/documents/{source}/{doc_id}/download")
def download_document_unified(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str = "灞曞巺",
    filename: str | None = None,
):
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        return mgr.download_ragflow_response(doc_id=doc_id, dataset=dataset, filename=filename, ctx=ctx)
    if src == "knowledge":
        return mgr.download_knowledge_response(doc_id=doc_id, ctx=ctx)
    raise HTTPException(status_code=400, detail="invalid_source")


@router.delete("/documents/{source}/{doc_id}", status_code=202)
async def delete_document_unified(
    source: str,
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str = "灞曞巺",
):
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        mgr.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)
        return {"message": "document_deleted"}
    if src == "knowledge":
        service = getattr(ctx.deps, "operation_approval_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
        try:
            return await service.create_request(
                operation_type="knowledge_file_delete",
                ctx=ctx,
                doc_id=doc_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=int(getattr(exc, "status_code", 400) or 400),
                detail=getattr(exc, "code", None) or str(exc) or "operation_approval_create_failed",
            ) from exc
    raise HTTPException(status_code=400, detail="invalid_source")


@router.post("/documents/knowledge/upload", response_model=OperationApprovalRequestBrief, status_code=202)
async def upload_knowledge_unified(
    request: Request,
    ctx: AuthContextDep,
    file: UploadFile = File(...),
):
    kb_ref = request.query_params.get("kb_id", "灞曞巺")
    service = getattr(ctx.deps, "operation_approval_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
    try:
        brief = await service.create_request(
            operation_type="knowledge_file_upload",
            ctx=ctx,
            upload_file=file,
            kb_ref=kb_ref,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 400) or 400),
            detail=getattr(exc, "code", None) or str(exc) or "operation_approval_create_failed",
        ) from exc
    return OperationApprovalRequestBrief(**brief)


@router.post("/documents/{source}/batch/download")
def batch_download_documents_unified(
    source: str,
    body: dict,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    src = (source or "").strip().lower()
    data = body or {}
    mgr = DocumentManager(deps)

    if src == "knowledge":
        return mgr.batch_download_knowledge_response(doc_ids=data.get("doc_ids", []), ctx=ctx)

    if src == "ragflow":
        return mgr.batch_download_ragflow_response(documents_info=data.get("documents", []), ctx=ctx)

    raise HTTPException(status_code=400, detail="invalid_source")
