from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.models.document import (
    BatchDocumentReviewRequest,
    BatchDocumentReviewResponse,
    DocumentResponse,
    DocumentReviewRequest,
)
from backend.services.audit_helpers import actor_fields_from_ctx


router = APIRouter()


def _to_document_response(updated_doc) -> DocumentResponse:
    return DocumentResponse(
        doc_id=updated_doc.doc_id,
        filename=updated_doc.filename,
        file_size=updated_doc.file_size,
        mime_type=updated_doc.mime_type,
        uploaded_by=updated_doc.uploaded_by,
        status=updated_doc.status,
        uploaded_at_ms=updated_doc.uploaded_at_ms,
        reviewed_by=updated_doc.reviewed_by,
        reviewed_at_ms=updated_doc.reviewed_at_ms,
        review_notes=updated_doc.review_notes,
        ragflow_doc_id=updated_doc.ragflow_doc_id,
        kb_id=updated_doc.kb_id,
    )


def _prepare_batch_doc_ids(doc_ids: list[str]) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    ordered_unique: list[str] = []
    duplicates: list[str] = []
    for raw in doc_ids or []:
        normalized = str(raw or "").strip()
        if not normalized:
            duplicates.append("")
            continue
        if normalized in seen:
            duplicates.append(normalized)
            continue
        seen.add(normalized)
        ordered_unique.append(normalized)
    return ordered_unique, duplicates


async def _reject_document_impl(doc_id: str, ctx: AuthContextDep, review_data: DocumentReviewRequest | None = None) -> DocumentResponse:
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail='文档不存在')

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != 'pending':
        raise HTTPException(status_code=400, detail='文档不是待审核状态')

    updated_doc = deps.kb_store.update_document_status(
        doc_id=doc_id,
        status='rejected',
        reviewed_by=ctx.payload.sub,
        review_notes=review_data.review_notes if review_data else None,
    )
    return _to_document_response(updated_doc)


@router.post('/documents/batch/reject', response_model=BatchDocumentReviewResponse)
async def reject_documents_batch(body: BatchDocumentReviewRequest, ctx: AuthContextDep):
    review_data = DocumentReviewRequest(review_notes=body.review_notes)
    succeeded_doc_ids = []
    failed_items = []
    unique_doc_ids, duplicate_doc_ids = _prepare_batch_doc_ids(body.doc_ids)

    for doc_id in unique_doc_ids:
        try:
            await _reject_document_impl(doc_id, ctx, review_data)
            succeeded_doc_ids.append(doc_id)
        except HTTPException as exc:
            failed_items.append({'doc_id': doc_id, 'detail': exc.detail, 'status_code': exc.status_code})
        except Exception as exc:  # pragma: no cover
            failed_items.append({'doc_id': doc_id, 'detail': str(exc), 'status_code': 500})

    for doc_id in duplicate_doc_ids:
        failed_items.append({'doc_id': doc_id, 'detail': 'duplicate_doc_id_in_batch', 'status_code': 409})

    audit = getattr(ctx.deps, "audit_log_store", None)
    if audit is not None:
        try:
            audit.log_event(
                action="document_review_batch",
                actor=ctx.payload.sub,
                source="knowledge",
                meta={
                    "operation": "reject",
                    "input_total": len(body.doc_ids or []),
                    "unique_total": len(unique_doc_ids),
                    "duplicate_total": len(duplicate_doc_ids),
                    "success_count": len(succeeded_doc_ids),
                    "failed_count": len(failed_items),
                },
                **actor_fields_from_ctx(ctx.deps, ctx),
            )
        except Exception:
            pass

    return BatchDocumentReviewResponse(
        total=len(body.doc_ids),
        success_count=len(succeeded_doc_ids),
        failed_count=len(failed_items),
        succeeded_doc_ids=succeeded_doc_ids,
        failed_items=failed_items,
    )


@router.post('/documents/{doc_id}/reject', response_model=DocumentResponse)
async def reject_document(doc_id: str, ctx: AuthContextDep, review_data: DocumentReviewRequest | None = None):
    return await _reject_document_impl(doc_id, ctx, review_data)
