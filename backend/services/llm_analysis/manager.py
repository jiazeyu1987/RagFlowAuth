from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMAnalysisError(Exception):
    code: str
    status_code: int = 500

    def __str__(self) -> str:
        return self.code


class LLMAnalysisManager:
    """
    Shared LLM chat-completion helper for download/analysis workflows.
    """

    def __init__(
        self,
        *,
        chat_service: Any,
        forced_id_env: str,
        forced_name_env: str,
        session_prefix: str,
    ):
        self._chat_service = chat_service
        self._forced_id_env = forced_id_env
        self._forced_name_env = forced_name_env
        self._session_prefix = session_prefix
        self._lock = threading.Lock()
        self._session_cache: dict[tuple[str, str], str] = {}

    @staticmethod
    def extract_completion_answer(payload: dict[str, Any] | None) -> str:
        def _walk(value: Any) -> str:
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, dict):
                for key in ("answer", "content", "text", "response", "message"):
                    if key in value:
                        got = _walk(value.get(key))
                        if got:
                            return got
                for key in ("data", "output", "result", "choices"):
                    if key in value:
                        got = _walk(value.get(key))
                        if got:
                            return got
                for child in value.values():
                    got = _walk(child)
                    if got:
                        return got
                return ""
            if isinstance(value, list):
                for item in value:
                    got = _walk(item)
                    if got:
                        return got
                return ""
            return ""

        if not isinstance(payload, dict):
            return ""
        return _walk(payload)

    @staticmethod
    def is_chat_method_unsupported_error(text: str) -> bool:
        lower = str(text or "").strip().lower()
        return "method chat not supported yet" in lower or "not supported yet" in lower

    def resolve_general_llm_chat_ids(self) -> list[str]:
        if self._chat_service is None:
            raise LLMAnalysisError("ragflow_chat_service_not_available")

        forced_id = str(os.getenv(self._forced_id_env, "") or "").strip()
        if forced_id:
            return [forced_id]

        forced_name = str(os.getenv(self._forced_name_env, "") or "").strip()
        preferred_names = [
            x
            for x in [forced_name, "[大模型]", "大模型", "[问题比对]", "问题比对", "[通用LLM]", "通用LLM", "小模型"]
            if x
        ]

        try:
            all_chats = self._chat_service.list_chats(page_size=200)
        except Exception:
            all_chats = []

        def _chat_name(chat: Any) -> str:
            return str((chat or {}).get("name") or "").strip()

        def _chat_id(chat: Any) -> str:
            return str((chat or {}).get("id") or "").strip()

        ordered: list[str] = []
        for target_name in preferred_names:
            normalized_target = str(target_name).strip().strip("[]").lower()
            for chat in all_chats or []:
                cname = _chat_name(chat)
                cid = _chat_id(chat)
                if not cname or not cid:
                    continue
                normalized_name = cname.strip().strip("[]").lower()
                if normalized_name == normalized_target and cid not in ordered:
                    ordered.append(cid)

        for chat in all_chats or []:
            cname = _chat_name(chat)
            cid = _chat_id(chat)
            if not cname or not cid:
                continue
            name_l = cname.lower()
            if ("llm" in name_l and ("通用" in cname or "general" in name_l)) or ("小模型" in cname):
                if cid not in ordered:
                    ordered.append(cid)

        if ordered:
            return ordered
        names = [str((c or {}).get("name") or "").strip() for c in (all_chats or []) if str((c or {}).get("name") or "").strip()]
        raise LLMAnalysisError(f"general_llm_chat_not_found; available_chats={names}")

    def get_or_create_session(
        self,
        *,
        actor: str,
        chat_id: str,
        force_new: bool = False,
        session_name: str | None = None,
    ) -> str:
        if self._chat_service is None:
            raise LLMAnalysisError("ragflow_chat_service_not_available")

        key = (str(actor), str(chat_id))
        if not force_new:
            with self._lock:
                existing = self._session_cache.get(key)
            if existing:
                return existing

        payload = self._chat_service._client.post_json_with_fallback(
            f"/api/v1/chats/{chat_id}/sessions",
            body={"name": str(session_name or f"{self._session_prefix}-{actor}")},
        )
        if not isinstance(payload, dict) or payload.get("code") != 0:
            raise LLMAnalysisError(f"llm_session_create_failed: {payload}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise LLMAnalysisError(f"llm_session_create_invalid_data: {payload}")
        sid = str(data.get("id") or "").strip()
        if not sid:
            raise LLMAnalysisError(f"llm_session_create_missing_id: {payload}")

        if not force_new:
            with self._lock:
                self._session_cache[key] = sid
        return sid

    def ask(self, *, actor: str, question: str, per_item_session_tag: str | None = None) -> str:
        if self._chat_service is None:
            raise LLMAnalysisError("ragflow_chat_service_not_available")

        last_error: Exception | None = None
        for chat_id in self.resolve_general_llm_chat_ids():
            try:
                session_id = self.get_or_create_session(
                    actor=actor,
                    chat_id=chat_id,
                    force_new=True,
                    session_name=f"{self._session_prefix}-{actor}-{per_item_session_tag or uuid.uuid4().hex[:8]}",
                )
                payload = self._chat_service._client.post_json_with_fallback(
                    f"/api/v1/chats/{chat_id}/completions",
                    body={"question": str(question or ""), "session_id": session_id, "stream": False},
                )
                if not isinstance(payload, dict) or payload.get("code") not in (0, None):
                    raise LLMAnalysisError(f"llm_completion_failed: {payload}")
                answer = self.extract_completion_answer(payload)
                if not answer:
                    raise LLMAnalysisError(f"llm_empty_answer: {payload}")
                answer_lower = str(answer).strip().lower()
                if answer_lower.startswith("**error**") or answer_lower.startswith("error:"):
                    if self.is_chat_method_unsupported_error(answer):
                        last_error = LLMAnalysisError(f"llm_error_response: {answer}")
                        continue
                    raise LLMAnalysisError(f"llm_error_response: {answer}")
                return answer
            except Exception as e:
                if self.is_chat_method_unsupported_error(str(e)):
                    last_error = e
                    continue
                if isinstance(e, LLMAnalysisError):
                    raise
                raise LLMAnalysisError(str(e)) from e

        if last_error is not None:
            raise LLMAnalysisError(f"llm_all_candidates_failed: {last_error}")
        raise LLMAnalysisError("llm_no_candidate_chat")
