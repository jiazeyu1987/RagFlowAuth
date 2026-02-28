from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.app.core.authz import AuthContextDep
from backend.services.patent_download.manager import LOCAL_PATENTS_KB_REF, PatentDownloadManager

router = APIRouter()


class PatentSourceConfig(BaseModel):
    enabled: bool = False
    limit: int = 10


class PatentSessionCreateRequest(BaseModel):
    keyword_text: str = ""
    use_and: bool = True
    auto_analyze: bool = False
    sources: dict[str, PatentSourceConfig] = Field(default_factory=dict)


class PatentAddRequest(BaseModel):
    kb_ref: str = LOCAL_PATENTS_KB_REF


class PatentHistoryDeleteRequest(BaseModel):
    history_key: str = ""


@router.post("/patent-download/sessions")
async def create_patent_download_session(
    body: PatentSessionCreateRequest,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    sources = {k: v.model_dump() for k, v in (body.sources or {}).items()}
    return mgr.create_session_and_download(
        ctx=ctx,
        keyword_text=body.keyword_text,
        use_and=bool(body.use_and),
        auto_analyze=bool(body.auto_analyze),
        source_configs=sources,
    )


@router.get("/patent-download/sessions/{session_id}")
async def get_patent_download_session(
    session_id: str,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.get_session_payload(session_id=session_id, ctx=ctx)


@router.post("/patent-download/sessions/{session_id}/stop")
async def stop_patent_download_session(
    session_id: str,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.stop_session_download(session_id=session_id, ctx=ctx)


@router.get("/patent-download/history/keywords")
async def list_patent_download_history_keywords(
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.list_history_keywords(ctx=ctx)


@router.get("/patent-download/history/keywords/{history_key}")
async def get_patent_download_history_items(
    history_key: str,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.get_history_group_payload(history_key=history_key, ctx=ctx)


@router.post("/patent-download/history/keywords/{history_key}/add-all-to-local-kb")
async def add_all_patent_history_items_to_local_kb(
    history_key: str,
    body: PatentAddRequest,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.add_history_group_to_local_kb(
        history_key=history_key,
        ctx=ctx,
        kb_ref=(body.kb_ref or LOCAL_PATENTS_KB_REF),
    )


@router.delete("/patent-download/history/keywords/{history_key}")
async def delete_patent_download_history_keyword(
    history_key: str,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.delete_history_group(history_key=history_key, ctx=ctx)


@router.post("/patent-download/history/keywords/delete")
async def delete_patent_download_history_keyword_post(
    body: PatentHistoryDeleteRequest,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.delete_history_group(history_key=(body.history_key or ""), ctx=ctx)


@router.get("/patent-download/sessions/{session_id}/items/{item_id}/preview")
async def preview_patent_download_item(
    session_id: str,
    item_id: int,
    ctx: AuthContextDep,
    render: str = "default",
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.get_item_preview_payload(session_id=session_id, item_id=item_id, ctx=ctx, render=render)


@router.get("/patent-download/sessions/{session_id}/items/{item_id}/download")
async def download_patent_download_item(
    session_id: str,
    item_id: int,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    content, filename, mime_type = mgr.get_item_download_payload(session_id=session_id, item_id=item_id, ctx=ctx)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": mgr.content_disposition(filename)},
    )


@router.post("/patent-download/sessions/{session_id}/items/{item_id}/add-to-local-kb")
async def add_patent_item_to_local_kb(
    session_id: str,
    item_id: int,
    body: PatentAddRequest,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.add_item_to_local_kb(
        session_id=session_id,
        item_id=item_id,
        ctx=ctx,
        kb_ref=(body.kb_ref or LOCAL_PATENTS_KB_REF),
        from_batch=False,
    )


@router.post("/patent-download/sessions/{session_id}/add-all-to-local-kb")
async def add_all_patent_items_to_local_kb(
    session_id: str,
    body: PatentAddRequest,
    ctx: AuthContextDep,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.add_all_to_local_kb(
        session_id=session_id,
        ctx=ctx,
        kb_ref=(body.kb_ref or LOCAL_PATENTS_KB_REF),
    )


@router.delete("/patent-download/sessions/{session_id}/items/{item_id}")
async def delete_patent_download_item(
    session_id: str,
    item_id: int,
    ctx: AuthContextDep,
    delete_local_kb: bool = True,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.delete_item(
        session_id=session_id,
        item_id=item_id,
        ctx=ctx,
        delete_local_kb=delete_local_kb,
    )


@router.delete("/patent-download/sessions/{session_id}")
async def delete_patent_download_session(
    session_id: str,
    ctx: AuthContextDep,
    delete_local_kb: bool = True,
):
    mgr = PatentDownloadManager(ctx.deps)
    return mgr.delete_session(session_id=session_id, ctx=ctx, delete_local_kb=delete_local_kb)
