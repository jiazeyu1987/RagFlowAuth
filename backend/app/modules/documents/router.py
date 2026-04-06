from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.request_params import require_non_empty_query_param
from backend.models.operation_approval import OperationApprovalRequestBrief, OperationApprovalRequestEnvelope
from backend.services.documents.document_manager import DocumentManager

router = APIRouter()


class ResultMessage(BaseModel):
    message: str


class ResultEnvelope(BaseModel):
    result: ResultMessage


def _wrap_operation_request(brief: dict) -> dict[str, dict]:
    return {"request": OperationApprovalRequestBrief(**brief).model_dump()}


def _wrap_result(message: str) -> dict[str, dict[str, str]]:
    return {"result": {"message": message}}


@router.get("/documents/{source}/{doc_id}/download")
def download_document_unified(
    source: str,
    doc_id: str,
    request: Request,
    ctx: AuthContextDep,
    filename: str | None = None,
):
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        dataset = require_non_empty_query_param(request, name="dataset", detail="missing_dataset")
        return mgr.download_ragflow_response(doc_id=doc_id, dataset=dataset, filename=filename, ctx=ctx)
    if src == "knowledge":
        return mgr.download_knowledge_response(doc_id=doc_id, ctx=ctx)
    raise HTTPException(status_code=400, detail="invalid_source")


@router.delete("/documents/{source}/{doc_id}", response_model=OperationApprovalRequestEnvelope | ResultEnvelope, status_code=202)
async def delete_document_unified(
    source: str,
    doc_id: str,
    request: Request,
    ctx: AuthContextDep,
):
    src = (source or "").strip().lower()
    mgr = DocumentManager(ctx.deps)
    if src == "ragflow":
        dataset_name = require_non_empty_query_param(request, name="dataset_name", detail="missing_dataset_name")
        mgr.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)
        return _wrap_result("document_deleted")
    if src == "knowledge":
        service = getattr(ctx.deps, "operation_approval_service", None)
        if service is None:
            raise HTTPException(status_code=500, detail="operation_approval_service_unavailable")
        try:
            brief = await service.create_request(
                operation_type="knowledge_file_delete",
                ctx=ctx,
                doc_id=doc_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=int(getattr(exc, "status_code", 400) or 400),
                detail=getattr(exc, "code", None) or str(exc) or "operation_approval_create_failed",
            ) from exc
        return _wrap_operation_request(brief)
    raise HTTPException(status_code=400, detail="invalid_source")


@router.post("/documents/knowledge/upload", response_model=OperationApprovalRequestEnvelope, status_code=202)
async def upload_knowledge_unified(
    request: Request,
    ctx: AuthContextDep,
    file: UploadFile = File(...),
):
    kb_ref = require_non_empty_query_param(request, name="kb_id", detail="missing_kb_id")
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
    return _wrap_operation_request(brief)


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
