import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import (
    assert_can_delete,
    assert_can_download,
    assert_can_upload,
    assert_kb_allowed,
)
from backend.models.document import (
    RagflowDocumentTransferBatchResult,
    RagflowDocumentTransferBatchResultEnvelope,
    RagflowDocumentTransferResult,
    RagflowDocumentTransferResultEnvelope,
)
from backend.services.documents.document_manager import DocumentManager
from backend.services.documents.models import DocumentRef

router = APIRouter()
logger = logging.getLogger(__name__)

class RagflowDocumentTransferRequest(BaseModel):
    source_dataset_name: str
    target_dataset_name: str
    operation: str = "copy"


class RagflowDocumentTransferItem(BaseModel):
    doc_id: str
    source_dataset_name: str
    target_dataset_name: str


class RagflowBatchTransferRequest(BaseModel):
    operation: str = "copy"
    items: list[RagflowDocumentTransferItem]


def _require_non_empty_value(value: str | None, detail: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail=detail)
    return normalized


def _normalize_document_list(documents: object) -> list:
    if not isinstance(documents, list):
        raise HTTPException(status_code=500, detail="documents_invalid_payload")
    return documents


def _wrap_result(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail="result_invalid_payload")
    return {"result": item}


def _wrap_status(doc_id: str, status: object) -> dict[str, dict[str, str]]:
    if not isinstance(status, str) or not status.strip():
        raise HTTPException(status_code=500, detail="document_status_invalid_payload")
    return {"status": {"doc_id": doc_id, "status": status}}


def _wrap_document(detail: object) -> dict[str, dict]:
    if not isinstance(detail, dict):
        raise HTTPException(status_code=500, detail="document_detail_invalid_payload")
    return {"document": detail}


def _wrap_transfer_result(item: object) -> dict[str, dict]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail="ragflow_document_transfer_invalid_payload")
    try:
        result = RagflowDocumentTransferResult.model_validate(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="ragflow_document_transfer_invalid_payload") from exc
    return {"result": result.model_dump()}


def _wrap_transfer_batch_result(item: object) -> dict[str, dict]:
    if not isinstance(item, dict):
        raise HTTPException(status_code=500, detail="ragflow_document_transfer_batch_invalid_payload")
    try:
        result = RagflowDocumentTransferBatchResult.model_validate(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="ragflow_document_transfer_batch_invalid_payload") from exc
    return {"result": result.model_dump()}


def _transfer_one_document(
    *,
    doc_id: str,
    source_dataset: str,
    target_dataset: str,
    operation: str,
    deps,
    snapshot,
) -> dict:
    op = str(operation or "").strip().lower()
    if op not in {"copy", "move"}:
        raise HTTPException(status_code=400, detail="invalid_operation")
    if not source_dataset or not target_dataset:
        raise HTTPException(status_code=400, detail="missing_dataset_name")

    source_kb = resolve_kb_ref(deps, source_dataset)
    target_kb = resolve_kb_ref(deps, target_dataset)
    assert_kb_allowed(snapshot, source_kb.variants)
    assert_kb_allowed(snapshot, target_kb.variants)
    assert_can_upload(snapshot)
    if op == "move":
        assert_can_delete(snapshot)
    if source_kb.dataset_id == target_kb.dataset_id and source_kb.name == target_kb.name:
        raise HTTPException(status_code=400, detail="source_and_target_dataset_same")

    content, filename = deps.ragflow_service.download_document(doc_id, source_dataset)
    if not content:
        raise HTTPException(status_code=404, detail="document_not_found")
    upload_name = filename or f"document_{doc_id}"

    target_doc_id = deps.ragflow_service.upload_document_blob(upload_name, content, kb_id=target_dataset)
    if not target_doc_id:
        raise HTTPException(status_code=502, detail="target_upload_failed")

    parse_triggered = False
    parse_error = ""
    if isinstance(target_doc_id, str) and target_doc_id and target_doc_id != "uploaded":
        try:
            parse_triggered = bool(
                deps.ragflow_service.parse_document(dataset_ref=target_dataset, document_id=target_doc_id)
            )
            if not parse_triggered:
                parse_error = "target_parse_trigger_failed"
        except Exception as exc:
            parse_triggered = False
            parse_error = str(exc)

    source_deleted = False
    if op == "move":
        source_deleted = bool(deps.ragflow_service.delete_document(doc_id, dataset_name=source_dataset))
        if not source_deleted:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "source_delete_failed_after_copy",
                    "source_doc_id": doc_id,
                    "target_doc_id": target_doc_id,
                },
            )

    return {
        "ok": True,
        "operation": op,
        "source_dataset_name": source_dataset,
        "target_dataset_name": target_dataset,
        "source_doc_id": doc_id,
        "target_doc_id": target_doc_id,
        "filename": upload_name,
        "source_deleted": source_deleted,
        "parse_triggered": parse_triggered,
        "parse_error": parse_error,
    }


@router.get("/documents")
def list_ragflow_documents(
    ctx: AuthContextDep,
    dataset_name: str | None = None,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    dataset_name = _require_non_empty_value(dataset_name, "missing_dataset_name")
    assert_kb_allowed(snapshot, resolve_kb_ref(deps, dataset_name).variants)
    documents = _normalize_document_list(deps.ragflow_service.list_documents(dataset_name))
    return {"documents": documents, "dataset": dataset_name}


@router.get("/documents/{doc_id}/status")
def get_document_status(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str | None = None,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    dataset_name = _require_non_empty_value(dataset_name, "missing_dataset_name")
    assert_kb_allowed(snapshot, resolve_kb_ref(deps, dataset_name).variants)
    status = deps.ragflow_service.get_document_status(doc_id, dataset_name)
    if status is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    return _wrap_status(doc_id, status)


@router.get("/documents/{doc_id}")
def get_document_detail(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str | None = None,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    dataset_name = _require_non_empty_value(dataset_name, "missing_dataset_name")
    assert_kb_allowed(snapshot, resolve_kb_ref(deps, dataset_name).variants)
    detail = deps.ragflow_service.get_document_detail(doc_id, dataset_name)
    if detail is None:
        raise HTTPException(status_code=404, detail="document_not_found")
    return _wrap_document(detail)


@router.get("/documents/{doc_id}/download")
def download_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str | None = None,
    filename: str = None,
):
    dataset = _require_non_empty_value(dataset, "missing_dataset")
    logger.info("[DOWNLOAD] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)
    mgr = DocumentManager(ctx.deps)
    return mgr.download_ragflow_response(doc_id=doc_id, dataset=dataset, filename=filename, ctx=ctx)


@router.get("/documents/{doc_id}/preview")
def preview_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset: str | None = None,
):
    dataset = _require_non_empty_value(dataset, "missing_dataset")
    logger.info("[PREVIEW] doc_id=%s dataset=%s user=%s", doc_id, dataset, ctx.payload.sub)

    snapshot = ctx.snapshot
    assert_kb_allowed(snapshot, resolve_kb_ref(ctx.deps, dataset).variants)
    mgr = DocumentManager(ctx.deps)
    return mgr.preview_payload(DocumentRef(source="ragflow", doc_id=doc_id, dataset_name=dataset))


@router.delete("/documents/{doc_id}")
def delete_ragflow_document(
    doc_id: str,
    ctx: AuthContextDep,
    dataset_name: str | None = None,
):
    dataset_name = _require_non_empty_value(dataset_name, "missing_dataset_name")
    logger.info("[DELETE] doc_id=%s dataset=%s user=%s", doc_id, dataset_name, ctx.payload.sub)
    mgr = DocumentManager(ctx.deps)
    mgr.delete_ragflow_document(doc_id=doc_id, dataset_name=dataset_name, ctx=ctx)
    return _wrap_result({"message": "document_deleted"})


@router.post("/documents/{doc_id}/transfer", response_model=RagflowDocumentTransferResultEnvelope)
def transfer_ragflow_document(
    doc_id: str,
    body: RagflowDocumentTransferRequest,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot

    return _wrap_transfer_result(
        _transfer_one_document(
            doc_id=doc_id,
            source_dataset=str(body.source_dataset_name or "").strip(),
            target_dataset=str(body.target_dataset_name or "").strip(),
            operation=str(body.operation or "").strip().lower(),
            deps=deps,
            snapshot=snapshot,
        )
    )


@router.post("/documents/transfer/batch", response_model=RagflowDocumentTransferBatchResultEnvelope)
def transfer_ragflow_documents_batch(
    body: RagflowBatchTransferRequest,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    operation = str(body.operation or "").strip().lower()
    if operation not in {"copy", "move"}:
        raise HTTPException(status_code=400, detail="invalid_operation")
    items = body.items or []
    if not items:
        raise HTTPException(status_code=400, detail="no_documents_selected")

    results: list[dict] = []
    failed: list[dict] = []
    for item in items:
        doc_id = str(item.doc_id or "").strip()
        source_dataset = str(item.source_dataset_name or "").strip()
        target_dataset = str(item.target_dataset_name or "").strip()
        if not doc_id:
            failed.append(
                {
                    "doc_id": doc_id,
                    "source_dataset_name": source_dataset,
                    "target_dataset_name": target_dataset,
                    "detail": "missing_doc_id",
                }
            )
            continue
        try:
            res = _transfer_one_document(
                doc_id=doc_id,
                source_dataset=source_dataset,
                target_dataset=target_dataset,
                operation=operation,
                deps=deps,
                snapshot=snapshot,
            )
            results.append(res)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            failed.append(
                {
                    "doc_id": doc_id,
                    "source_dataset_name": source_dataset,
                    "target_dataset_name": target_dataset,
                    "detail": detail,
                }
            )

    return _wrap_transfer_batch_result(
        {
            "ok": len(failed) == 0,
            "operation": operation,
            "total": len(items),
            "success_count": len(results),
            "failed_count": len(failed),
            "results": results,
            "failed": failed,
        }
    )


@router.post("/documents/batch/download")
def batch_download_documents(
    body: dict,
    ctx: AuthContextDep,
):
    deps = ctx.deps
    data = body or {}
    documents_info = data.get("documents", [])
    logger.info("[BATCH DOWNLOAD] count=%s user=%s", len(documents_info), ctx.payload.sub)

    snapshot = ctx.snapshot
    assert_can_download(snapshot)

    if not documents_info:
        raise HTTPException(status_code=400, detail="no_documents_selected")

    normalized_documents_info: list[dict] = []
    for doc_info in documents_info:
        if not isinstance(doc_info, dict):
            raise HTTPException(status_code=400, detail="invalid_document_item")
        dataset = _require_non_empty_value(doc_info.get("dataset"), "missing_dataset")
        assert_kb_allowed(snapshot, resolve_kb_ref(deps, dataset).variants)
        normalized_documents_info.append({**doc_info, "dataset": dataset})

    zip_content, filename = deps.ragflow_service.batch_download_documents(normalized_documents_info)
    if zip_content is None:
        logger.error("[BATCH DOWNLOAD] Failed to create zip - service returned None")
        raise HTTPException(status_code=500, detail="\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25")

    for doc_info in normalized_documents_info:
        doc_id = doc_info.get("doc_id") or doc_info.get("id")
        doc_name = doc_info.get("name", "unknown")
        dataset = doc_info["dataset"]
        kb_info = resolve_kb_ref(deps, dataset)

        deps.download_log_store.log_download(
            doc_id=doc_id,
            filename=doc_name,
            kb_id=(kb_info.dataset_id or dataset),
            downloaded_by=ctx.payload.sub,
            ragflow_doc_id=doc_id,
            is_batch=True,
            kb_dataset_id=kb_info.dataset_id,
            kb_name=(kb_info.name or dataset),
        )

    return Response(
        content=zip_content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )
