from typing import Optional

from fastapi import APIRouter

from backend.app.core.authz import AuthContextDep
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.permission_resolver import assert_kb_allowed

router = APIRouter()


@router.get("/downloads")
async def list_downloads(
    ctx: AuthContextDep,
    kb_id: Optional[str] = None,
    downloaded_by: Optional[str] = None,
    limit: int = 100,
):
    deps = ctx.deps
    if kb_id:
        assert_kb_allowed(ctx.snapshot, kb_id)
        kb_refs = list(resolve_kb_ref(deps, kb_id).variants)
    else:
        kb_refs = None

    if not ctx.snapshot.is_admin:
        downloaded_by = ctx.payload.sub

    downloads = deps.download_log_store.list_downloads(kb_refs=kb_refs, downloaded_by=downloaded_by, limit=limit)

    return {
        "downloads": [
            {
                "id": d.id,
                "doc_id": d.doc_id,
                "filename": d.filename,
                "kb_id": (d.kb_name or d.kb_id),
                "downloaded_by": d.downloaded_by,
                "downloaded_at_ms": d.downloaded_at_ms,
                "ragflow_doc_id": d.ragflow_doc_id,
                "is_batch": d.is_batch,
            }
            for d in downloads
        ],
        "count": len(downloads),
    }

