from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.core.authz import AuthContextDep
from backend.app.core.permission_resolver import assert_can_review, assert_kb_allowed
from backend.models.document import (
    BatchDocumentReviewRequest,
    BatchDocumentReviewResponse,
    DocumentResponse,
    DocumentReviewRequest,
)


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


def _approve_document_impl(doc_id: str, ctx: AuthContextDep, review_data: DocumentReviewRequest | None = None) -> DocumentResponse:
    import logging

    logger = logging.getLogger(__name__)
    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot
    assert_can_review(snapshot)

    logger.info('[APPROVE] User %s approving doc %s', user.username, doc_id)

    doc = deps.kb_store.get_document(doc_id)
    if not doc:
        logger.error('[APPROVE] Document not found: %s', doc_id)
        raise HTTPException(status_code=404, detail='文档不存在')

    assert_kb_allowed(snapshot, doc.kb_id)

    if doc.status != 'pending':
        logger.error('[APPROVE] Document status is not pending: %s', doc.status)
        raise HTTPException(status_code=400, detail='文档不是待审核状态')

    try:
        if not Path(doc.file_path).exists():
            logger.error('[APPROVE] Local file not found: %s', doc.file_path)
            raise HTTPException(status_code=404, detail='本地文件不存在')

        with open(doc.file_path, 'rb') as f:
            file_content = f.read()

        ragflow_doc_id = deps.ragflow_service.upload_document_blob(
            file_filename=doc.filename,
            file_content=file_content,
            kb_id=doc.kb_id,
        )
        if not ragflow_doc_id:
            raise HTTPException(status_code=500, detail='上传到RAGFlow失败')

        dataset_ref = doc.kb_dataset_id or doc.kb_id or (doc.kb_name or '')
        if ragflow_doc_id and ragflow_doc_id != 'uploaded':
            try:
                ok = deps.ragflow_service.parse_document(dataset_ref=dataset_ref, document_id=ragflow_doc_id)
                if not ok:
                    logger.warning(
                        '[APPROVE] Parse trigger failed: doc_id=%s ragflow_doc_id=%s dataset_ref=%s',
                        doc_id,
                        ragflow_doc_id,
                        dataset_ref,
                    )
            except Exception as e:
                logger.warning(
                    '[APPROVE] Parse trigger exception: doc_id=%s ragflow_doc_id=%s dataset_ref=%s err=%s',
                    doc_id,
                    ragflow_doc_id,
                    dataset_ref,
                    e,
                )
        else:
            logger.warning('[APPROVE] Skip parse trigger: ragflow_doc_id is not available (%s)', ragflow_doc_id)

        updated_doc = deps.kb_store.update_document_status(
            doc_id=doc_id,
            status='approved',
            reviewed_by=ctx.payload.sub,
            review_notes=review_data.review_notes if review_data else None,
            ragflow_doc_id=ragflow_doc_id,
        )
        return _to_document_response(updated_doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception('[APPROVE] Exception during approval: %s', e)
        raise HTTPException(status_code=500, detail=f'审核失败: {str(e)}')


@router.post('/documents/batch/approve', response_model=BatchDocumentReviewResponse)
def approve_documents_batch(body: BatchDocumentReviewRequest, ctx: AuthContextDep):
    review_data = DocumentReviewRequest(review_notes=body.review_notes)
    succeeded_doc_ids = []
    failed_items = []

    for doc_id in body.doc_ids:
        try:
            _approve_document_impl(doc_id, ctx, review_data)
            succeeded_doc_ids.append(doc_id)
        except HTTPException as exc:
            failed_items.append({'doc_id': doc_id, 'detail': exc.detail, 'status_code': exc.status_code})
        except Exception as exc:  # pragma: no cover
            failed_items.append({'doc_id': doc_id, 'detail': str(exc), 'status_code': 500})

    return BatchDocumentReviewResponse(
        total=len(body.doc_ids),
        success_count=len(succeeded_doc_ids),
        failed_count=len(failed_items),
        succeeded_doc_ids=succeeded_doc_ids,
        failed_items=failed_items,
    )


@router.post('/documents/{doc_id}/approve', response_model=DocumentResponse)
def approve_document(doc_id: str, ctx: AuthContextDep, review_data: DocumentReviewRequest | None = None):
    return _approve_document_impl(doc_id, ctx, review_data)
