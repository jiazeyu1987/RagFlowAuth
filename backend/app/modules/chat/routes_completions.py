from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.core.authz import AuthContextDep
from backend.services.audit_helpers import (
    build_audit_evidence_refs,
    first_evidence_document_context,
    log_quality_audit_event,
)

from .shared import ChatCompletionRequest, assert_chat_access
from .source_builder import build_retrieval_sources, persist_assistant_sources


router = APIRouter()
logger = logging.getLogger(__name__)
LOG_AS_WARNING = str(os.getenv("RAGFLOWAUTH_DEBUG_SSE", "0")).strip() == "1"


def _chat_log(message: str, *args) -> None:
    if LOG_AS_WARNING:
        logger.warning(message, *args)
    else:
        logger.info(message, *args)


def _sse_frame(payload: dict) -> str:
    # SSE protocol requires real line delimiters, not escaped "\\n".
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _extract_session_and_answer(chunk: dict, current_session_id: str | None) -> tuple[str | None, str]:
    next_session_id = current_session_id
    assistant_answer = ""

    try:
        data = chunk.get("data")
        if not isinstance(data, dict):
            return next_session_id, assistant_answer

        if not next_session_id:
            sid = data.get("session_id") or data.get("sessionId") or data.get("session")
            if sid:
                next_session_id = str(sid).strip() or None

        ans = data.get("answer")
        if isinstance(ans, str) and ans:
            assistant_answer = ans
    except Exception:
        return next_session_id, ""

    return next_session_id, assistant_answer


@router.post("/chats/{chat_id}/completions")
async def chat_completion(
    chat_id: str,
    request: Request,
    body: ChatCompletionRequest,
    ctx: AuthContextDep,
):
    trace_id = str(request.headers.get("X-Chat-Trace-Id") or "").strip() or "-"
    request_id = str(getattr(request.state, "request_id", "") or "").strip() or "-"
    _chat_log(
        "[CHAT][recv] request_id=%s trace_id=%s chat_id=%s session_id=%s question_len=%s question_preview=%s",
        request_id,
        trace_id,
        chat_id,
        body.session_id,
        len(str(body.question or "")),
        str(body.question or "")[:80],
    )

    deps = ctx.deps
    user = ctx.user
    snapshot = ctx.snapshot

    if not snapshot.is_admin:
        try:
            assert_chat_access(snapshot, chat_id=chat_id)
        except HTTPException:
            logger.warning("[CHAT] User %s has no permission for chat %s", user.username, chat_id)
            raise

    if not body.question:
        logger.warning("[CHAT] Empty question received")
        raise HTTPException(status_code=400, detail="question_required")

    async def generate():
        sources_task: asyncio.Task | None = None
        effective_session_id = str(body.session_id or "").strip() or None
        assistant_text_for_hash = ""
        built_sources: list[dict] = []
        sources_sent = False
        chunk_index = 0
        emitted_index = 0
        stream_started_at = time.perf_counter()

        try:
            _chat_log(
                "[CHAT][stream-start] request_id=%s trace_id=%s chat_id=%s session_id=%s",
                request_id,
                trace_id,
                chat_id,
                body.session_id,
            )

            try:
                sources_task = asyncio.create_task(
                    asyncio.to_thread(
                        build_retrieval_sources,
                        deps=deps,
                        snapshot=snapshot,
                        question=body.question,
                        logger=logger,
                    )
                )
            except Exception:
                sources_task = None

            async for chunk in deps.ragflow_chat_service.chat(
                chat_id=chat_id,
                question=body.question,
                stream=body.stream,
                session_id=body.session_id,
                user_id=user.user_id,
                trace_id=trace_id,
            ):
                chunk_index += 1
                if isinstance(chunk, dict):
                    effective_session_id, ans = _extract_session_and_answer(chunk, effective_session_id)
                    if ans:
                        assistant_text_for_hash = ans
                    data_obj = chunk.get("data") if isinstance(chunk.get("data"), dict) else {}
                    answer_len = len(str(data_obj.get("answer") or ""))
                    _chat_log(
                        "[CHAT][chunk-in] request_id=%s trace_id=%s idx=%s code=%s answer_len=%s keys=%s",
                        request_id,
                        trace_id,
                        chunk_index,
                        chunk.get("code"),
                        answer_len,
                        list(chunk.keys())[:8],
                    )
                else:
                    _chat_log(
                        "[CHAT][chunk-in] request_id=%s trace_id=%s idx=%s type=%s",
                        request_id,
                        trace_id,
                        chunk_index,
                        type(chunk).__name__,
                    )

                try:
                    if sources_task and (not sources_sent) and sources_task.done():
                        sources_sent = True
                        built_sources = sources_task.result() or []
                        if built_sources:
                            payload = {"code": 0, "data": {"sources": built_sources}}
                            frame = _sse_frame(payload)
                            emitted_index += 1
                            _chat_log(
                                "[CHAT][emit] request_id=%s trace_id=%s idx=%s kind=sources count=%s frame_len=%s",
                                request_id,
                                trace_id,
                                emitted_index,
                                len(built_sources),
                                len(frame),
                            )
                            yield frame
                except Exception as exc:
                    sources_sent = True
                    logger.warning("[CHAT] Failed to emit sources event: %s", exc)

                frame = _sse_frame(chunk if isinstance(chunk, dict) else {"code": 0, "data": {"answer": str(chunk)}})
                emitted_index += 1
                _chat_log(
                    "[CHAT][emit] request_id=%s trace_id=%s idx=%s kind=chunk source_idx=%s frame_len=%s",
                    request_id,
                    trace_id,
                    emitted_index,
                    chunk_index,
                    len(frame),
                )
                yield frame

            try:
                if sources_task and not sources_sent:
                    sources_sent = True
                    if sources_task.done():
                        built_sources = sources_task.result() or []
                    else:
                        built_sources = await sources_task or []

                persist_assistant_sources(
                    deps=deps,
                    chat_id=chat_id,
                    session_id=effective_session_id,
                    assistant_text=assistant_text_for_hash,
                    sources=built_sources,
                    logger=logger,
                )
                evidence_refs = build_audit_evidence_refs(
                    built_sources,
                    default_role="chat_citation",
                )
                doc_context = first_evidence_document_context(evidence_refs)
                log_quality_audit_event(
                    deps=deps,
                    ctx=ctx,
                    action="smart_chat_completion",
                    source="smart_chat",
                    resource_type="chat_session",
                    resource_id=effective_session_id or (trace_id if trace_id != "-" else chat_id),
                    event_type="completion",
                    request_id=(request_id if request_id != "-" else None),
                    before={
                        "chat_id": chat_id,
                        "session_id": effective_session_id,
                        "trace_id": trace_id if trace_id != "-" else None,
                        "question": body.question,
                    },
                    after={
                        "answer_length": len(str(assistant_text_for_hash or "")),
                        "source_count": len(evidence_refs),
                    },
                    doc_id=doc_context["doc_id"],
                    filename=doc_context["filename"],
                    kb_id=doc_context["kb_id"],
                    kb_dataset_id=doc_context["kb_dataset_id"],
                    kb_name=doc_context["kb_name"],
                    evidence_refs=evidence_refs,
                    meta={
                        "chat_id": chat_id,
                        "session_id": effective_session_id,
                        "trace_id": trace_id if trace_id != "-" else None,
                        "question": body.question,
                        "answer_excerpt": str(assistant_text_for_hash or "")[:400],
                        "answer_length": len(str(assistant_text_for_hash or "")),
                        "source_count": len(evidence_refs),
                    },
                )
                elapsed_ms = int((time.perf_counter() - stream_started_at) * 1000)
                _chat_log(
                    "[CHAT][stream-end] request_id=%s trace_id=%s chat_id=%s session_id=%s chunks_in=%s emitted=%s answer_len=%s elapsed_ms=%s",
                    request_id,
                    trace_id,
                    chat_id,
                    effective_session_id,
                    chunk_index,
                    emitted_index,
                    len(str(assistant_text_for_hash or "")),
                    elapsed_ms,
                )
            except Exception:
                logger.exception("[CHAT] Failed to persist sources after streaming")
        except Exception as exc:
            logger.error("[CHAT] Error during chat trace_id=%s request_id=%s: %s", trace_id, request_id, exc, exc_info=True)
            error_chunk = {"code": -1, "message": str(exc)}
            yield _sse_frame(error_chunk)
        finally:
            if sources_task and not sources_task.done():
                try:
                    sources_task.cancel()
                except Exception:
                    pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
