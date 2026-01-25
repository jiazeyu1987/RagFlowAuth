from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.models.document import DocumentResponse, DocumentReviewRequest


router = APIRouter()


@router.post("/documents/{doc_id}/reject", response_model=DocumentResponse)
async def reject_document(
    doc_id: str,
    ctx: AuthContextDep,
    review_data: DocumentReviewRequest = None,
):
    deps = ctx.deps
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != "pending":
        raise HTTPException(status_code=400, detail="文档不是待审核状态")

    updated_doc = deps.kb_store.update_document_status(
        doc_id=doc_id,
        status="rejected",
        reviewed_by=ctx.payload.sub,
        review_notes=review_data.review_notes if review_data else None,
    )

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

