from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.core.authz import AuthContextDep
from backend.services.egress_policy_engine import EgressPolicyEngine
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import FLAG_EGRESS_POLICY_ENABLED, SystemFeatureFlagStore

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


_SENSITIVITY_LEVEL_LABELS = {
    "none": "无",
    "low": "低敏",
    "medium": "中敏",
    "high": "高敏",
}


def _normalize_hit_rules(hit_rules: Any) -> list[dict[str, Any]]:
    if not isinstance(hit_rules, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in hit_rules:
        if not isinstance(item, dict):
            continue
        level = str(item.get("level") or "").strip().lower()
        rule = str(item.get("rule") or "").strip()
        count_raw = item.get("count")
        try:
            count = int(count_raw)
        except Exception:
            count = 0
        if not level or not rule or count <= 0:
            continue
        normalized.append(
            {
                "level": level,
                "rule": rule,
                "count": count,
            }
        )
    return normalized


def _translate_policy_block_reason(reason: str | None) -> str:
    text = str(reason or "").strip()
    if not text:
        return "命中安全策略，已拦截"
    if "high_sensitive" in text:
        return "命中高敏策略，已执行拦截"
    if "model_not_allowed" in text:
        if ":" in text:
            model_name = str(text.split(":", 1)[1] or "").strip()
            if model_name:
                return f"模型未通过准入校验：{model_name}"
        return "模型未通过准入校验"
    if "egress_blocked_by_mode" in text:
        return "外发模式不允许当前目标地址"
    return f"策略拦截：{text}"


def _build_safety_chunk(
    *,
    stage: str,
    status: str,
    summary: str,
    detail: str = "",
    blocked: bool = False,
    done: bool = False,
    payload_level: str = "",
    masked: bool | None = None,
    hit_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    security = {
        "security_stage": stage,
        "security_status": status,
        "summary": summary,
        "detail": detail,
        "blocked": bool(blocked),
        "done": bool(done),
    }
    if payload_level:
        security["payload_level"] = payload_level
    if masked is not None:
        security["masked"] = bool(masked)
    if isinstance(hit_rules, list) and hit_rules:
        security["hit_rules"] = hit_rules
    return {"code": 0, "data": {"security": security}}


def _build_chat_safety_plan(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        decision = EgressPolicyEngine().evaluate_payload(payload)
    except Exception as exc:
        logger.warning("[CHAT] Safety plan skipped because egress policy evaluation failed: %s", exc)
        return None

    try:
        feature_enabled = SystemFeatureFlagStore().is_enabled(FLAG_EGRESS_POLICY_ENABLED, default=True)
    except Exception:
        feature_enabled = True

    try:
        policy = EgressPolicyStore().get()
    except Exception:
        policy = None

    sensitivity_enabled = bool(getattr(policy, "sensitive_classification_enabled", False)) if policy else False
    auto_desensitize_enabled = bool(getattr(policy, "auto_desensitize_enabled", False)) if policy else False
    hit_rules = _normalize_hit_rules(getattr(decision, "hit_rules", []))
    hit_count = sum(int(item.get("count") or 0) for item in hit_rules)
    payload_level = str(getattr(decision, "payload_level", "none") or "none").strip().lower()
    payload_level_label = _SENSITIVITY_LEVEL_LABELS.get(payload_level, "无")

    events_before_stream: list[dict[str, Any]] = []
    final_allow_event: dict[str, Any] | None = None

    if not feature_enabled:
        events_before_stream.extend(
            [
                _build_safety_chunk(
                    stage="classify",
                    status="skipped",
                    summary="外发安全策略未启用",
                    detail="当前已跳过敏感分级",
                ),
                _build_safety_chunk(
                    stage="desensitize",
                    status="skipped",
                    summary="外发安全策略未启用",
                    detail="当前已跳过脱敏处理",
                ),
                _build_safety_chunk(
                    stage="intercept",
                    status="success",
                    summary="安全流程完成，已放行回复",
                    detail="当前策略未启用，默认放行",
                    done=True,
                ),
            ]
        )
        return {
            "events_before_stream": events_before_stream,
            "final_allow_event": None,
            "blocked": False,
        }

    if sensitivity_enabled:
        if hit_count > 0:
            classify_detail = f"命中 {hit_count} 条规则，分级结果：{payload_level_label}"
        else:
            classify_detail = "未命中敏感规则，分级结果：无"
        events_before_stream.append(
            _build_safety_chunk(
                stage="classify",
                status="success",
                summary="敏感分级完成",
                detail=classify_detail,
                payload_level=payload_level,
                hit_rules=hit_rules,
            )
        )
    else:
        events_before_stream.append(
            _build_safety_chunk(
                stage="classify",
                status="skipped",
                summary="已跳过敏感分级",
                detail="管理员未启用敏感分级策略",
            )
        )

    if not sensitivity_enabled:
        events_before_stream.append(
            _build_safety_chunk(
                stage="desensitize",
                status="skipped",
                summary="已跳过脱敏处理",
                detail="敏感分级未启用，脱敏阶段自动跳过",
            )
        )
    elif not auto_desensitize_enabled:
        events_before_stream.append(
            _build_safety_chunk(
                stage="desensitize",
                status="skipped",
                summary="已跳过脱敏处理",
                detail="管理员未启用自动脱敏策略",
                payload_level=payload_level,
                hit_rules=hit_rules,
            )
        )
    else:
        desensitize_detail = (
            f"已完成自动脱敏，命中 {hit_count} 条规则"
            if bool(getattr(decision, "masked", False))
            else "未发现需要脱敏的内容"
        )
        events_before_stream.append(
            _build_safety_chunk(
                stage="desensitize",
                status="success",
                summary="脱敏处理完成",
                detail=desensitize_detail,
                payload_level=payload_level,
                masked=bool(getattr(decision, "masked", False)),
                hit_rules=hit_rules,
            )
        )

    events_before_stream.append(
        _build_safety_chunk(
            stage="intercept",
            status="running",
            summary="正在执行拦截检查...",
            detail="正在进行策略比对与放行判定",
            payload_level=payload_level,
            masked=bool(getattr(decision, "masked", False)),
            hit_rules=hit_rules,
        )
    )

    if not bool(getattr(decision, "allowed", False)):
        events_before_stream.append(
            _build_safety_chunk(
                stage="intercept",
                status="failed",
                summary="命中安全策略，已拦截回复",
                detail=_translate_policy_block_reason(getattr(decision, "blocked_reason", "")),
                blocked=True,
                done=True,
                payload_level=payload_level,
                masked=bool(getattr(decision, "masked", False)),
                hit_rules=hit_rules,
            )
        )
        return {
            "events_before_stream": events_before_stream,
            "final_allow_event": None,
            "blocked": True,
        }

    final_allow_event = _build_safety_chunk(
        stage="intercept",
        status="success",
        summary="安全流程完成，已放行回复",
        detail="通过拦截检查，允许继续生成回答",
        done=True,
        payload_level=payload_level,
        masked=bool(getattr(decision, "masked", False)),
        hit_rules=hit_rules,
    )
    return {
        "events_before_stream": events_before_stream,
        "final_allow_event": final_allow_event,
        "blocked": False,
    }


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
        safety_plan: dict[str, Any] | None = None
        safety_allow_emitted = False

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

            try:
                outbound_payload: dict[str, Any] = {"question": body.question, "stream": body.stream}
                if effective_session_id:
                    outbound_payload["session_id"] = effective_session_id
                if user.user_id:
                    outbound_payload["user_id"] = user.user_id
                safety_plan = _build_chat_safety_plan(outbound_payload)
            except Exception as exc:
                logger.warning("[CHAT] Failed to build safety plan: %s", exc)
                safety_plan = None

            try:
                safety_events = list((safety_plan or {}).get("events_before_stream") or [])
                for event_payload in safety_events:
                    frame = _sse_frame(event_payload)
                    emitted_index += 1
                    _chat_log(
                        "[CHAT][emit] request_id=%s trace_id=%s idx=%s kind=safety frame_len=%s",
                        request_id,
                        trace_id,
                        emitted_index,
                        len(frame),
                    )
                    yield frame
            except Exception as exc:
                logger.warning("[CHAT] Failed to emit safety events: %s", exc)

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
                    answer_len = len(str(data_obj.get("answer") or data_obj.get("content") or data_obj.get("text") or ""))
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

                if safety_plan and (not safety_allow_emitted):
                    allow_event = safety_plan.get("final_allow_event")
                    if isinstance(allow_event, dict):
                        frame = _sse_frame(allow_event)
                        emitted_index += 1
                        safety_allow_emitted = True
                        _chat_log(
                            "[CHAT][emit] request_id=%s trace_id=%s idx=%s kind=safety-final frame_len=%s",
                            request_id,
                            trace_id,
                            emitted_index,
                            len(frame),
                        )
                        yield frame

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

            if safety_plan and (not safety_allow_emitted):
                allow_event = safety_plan.get("final_allow_event")
                if isinstance(allow_event, dict):
                    frame = _sse_frame(allow_event)
                    emitted_index += 1
                    safety_allow_emitted = True
                    _chat_log(
                        "[CHAT][emit] request_id=%s trace_id=%s idx=%s kind=safety-tail frame_len=%s",
                        request_id,
                        trace_id,
                        emitted_index,
                        len(frame),
                    )
                    yield frame

            try:
                if sources_task and (not sources_sent) and sources_task.done():
                    sources_sent = True
                    built_sources = sources_task.result() or []

                persist_assistant_sources(
                    deps=deps,
                    chat_id=chat_id,
                    session_id=effective_session_id,
                    assistant_text=assistant_text_for_hash,
                    sources=built_sources,
                    logger=logger,
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
            if safety_plan and (not safety_allow_emitted):
                try:
                    fail_event = _build_safety_chunk(
                        stage="intercept",
                        status="failed",
                        summary="安全流程异常中断",
                        detail="对话流程异常终止，请稍后重试",
                        blocked=True,
                        done=True,
                    )
                    emitted_index += 1
                    yield _sse_frame(fail_event)
                except Exception:
                    pass
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
