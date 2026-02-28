from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import html
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.app.core.permission_resolver import assert_can_delete, assert_can_upload, assert_kb_allowed
from backend.services.audit_helpers import actor_fields_from_ctx
from backend.services.documents.document_manager import DocumentManager
from backend.services.paper_download.store import PaperDownloadStore, item_to_dict, session_to_dict
from backend.services.unified_preview import build_preview_payload

from .sources import ArxivSource, EuropePmcSource, OpenAlexSource, PaperCandidate, PaperSourceError, PubMedSource


LOCAL_PAPERS_KB_REF = "[本地论文]"


class PaperDownloadManager:
    _SOURCE_ORDER = ("arxiv", "pubmed", "europe_pmc", "openalex")
    _MIME_TYPE_DEFAULT = "application/pdf"
    _DOWNLOAD_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )
    _jobs_lock = threading.Lock()
    _jobs: dict[str, threading.Thread] = {}
    _cancelled_sessions: set[str] = set()
    _stop_requested_sessions: set[str] = set()
    _llm_lock = threading.Lock()
    _llm_session_cache: dict[tuple[str, str], str] = {}

    @staticmethod
    def _is_downloaded_status(status: str | None) -> bool:
        return str(status or "").strip().lower() in {"downloaded", "downloaded_cached"}

    @staticmethod
    def _is_true(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def __init__(self, deps: Any):
        self.deps = deps
        self.store: PaperDownloadStore = getattr(deps, "paper_download_store", None) or PaperDownloadStore()
        self._arxiv_source = ArxivSource()
        self._pubmed_source = PubMedSource()
        self._europe_pmc_source = EuropePmcSource()
        self._openalex_source = OpenAlexSource()
        self._sources = {
            "arxiv": self._arxiv_source,
            "pubmed": self._pubmed_source,
            "europe_pmc": self._europe_pmc_source,
            "openalex": self._openalex_source,
        }

    @staticmethod
    def parse_keywords(keyword_text: str) -> list[str]:
        parts = re.split(r"[,;\n\r，；]+", str(keyword_text or ""))
        out: list[str] = []
        seen: set[str] = set()
        for part in parts:
            v = str(part or "").strip()
            if not v:
                continue
            key = v.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(v)
        return out

    @staticmethod
    def _build_query(keywords: list[str], use_and: bool) -> str:
        if not keywords:
            return ""
        if len(keywords) == 1:
            return keywords[0]
        return " ".join(keywords) if use_and else " OR ".join(keywords)

    @staticmethod
    def _build_quoted_query(keywords: list[str], use_and: bool) -> str:
        quoted: list[str] = []
        for raw in keywords or []:
            kw = str(raw or "").strip()
            if not kw:
                continue
            if len(kw) >= 2 and kw.startswith('"') and kw.endswith('"'):
                quoted.append(kw)
            else:
                quoted.append(f'"{kw}"')
        if not quoted:
            return ""
        if len(quoted) == 1:
            return quoted[0]
        return " ".join(quoted) if use_and else " OR ".join(quoted)

    @staticmethod
    def _contains_chinese(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))

    @staticmethod
    def _normalize_source_configs(source_configs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        src = source_configs if isinstance(source_configs, dict) else {}
        out: dict[str, dict[str, Any]] = {}
        for key in ("arxiv", "pubmed", "europe_pmc", "openalex"):
            cfg = src.get(key)
            if not isinstance(cfg, dict):
                cfg = {}
            enabled = bool(cfg.get("enabled", False))
            limit = int(cfg.get("limit", 30) or 30)
            out[key] = {"enabled": enabled, "limit": max(1, min(limit, 1000))}
        return out

    @staticmethod
    def _safe_filename(name: str, fallback: str) -> str:
        base = str(name or "").strip() or str(fallback or "paper").strip()
        base = re.sub(r"[\\/:*?\"<>|]+", "_", base).strip(" .")
        if not base:
            base = "paper"
        if not base.lower().endswith(".pdf"):
            base += ".pdf"
        return base

    @staticmethod
    def _content_disposition(filename: str) -> str:
        try:
            filename.encode("ascii")
            return f'attachment; filename="{filename}"'
        except UnicodeEncodeError:
            ascii_filename = filename.encode("ascii", "replace").decode("ascii")
            encoded_filename = urllib.parse.quote(filename)
            return f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"

    def _download_root(self) -> Path:
        root = resolve_repo_path(getattr(settings, "PAPER_DOWNLOAD_DIR", "data/paper_downloads"))
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _session_dir(self, *, actor_id: str, session_id: str) -> Path:
        path = self._download_root() / actor_id / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _download_pdf_bytes(self, url: str) -> bytes:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._DOWNLOAD_USER_AGENT,
                "Accept": "application/pdf,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read()

    def _serialize_item(self, item: Any) -> dict[str, Any]:
        data = item_to_dict(item)
        path = str(data.pop("file_path", "") or "")
        data["has_file"] = bool(path and os.path.exists(path))
        analysis_path = str(data.get("analysis_file_path") or "")
        data["has_analysis_file"] = bool(analysis_path and os.path.exists(analysis_path))
        data["downloaded_before"] = str(data.get("status") or "") == "downloaded_cached"
        return data

    @staticmethod
    def _strip_html(value: str | None) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _kb_target_candidates(cls, kb_ref: str, kb_info: Any) -> list[str]:
        raw = str(kb_ref or "").strip()
        bracket_inner = ""
        m = re.fullmatch(r"\[(.+)\]", raw)
        if m:
            bracket_inner = str(m.group(1) or "").strip()
        ordered: list[str] = []
        for v in (
            getattr(kb_info, "dataset_id", None),
            getattr(kb_info, "name", None),
            raw,
            bracket_inner,
        ):
            value = str(v or "").strip()
            if value and value not in ordered:
                ordered.append(value)
        return ordered

    @staticmethod
    def _item_key(candidate: PaperCandidate) -> str:
        return (
            str(candidate.patent_id or "").strip()
            or str(candidate.publication_number or "").strip()
            or str(candidate.title or "").strip()
        )

    @staticmethod
    def _normalize_match_text(value: str | None) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = re.sub(r"\s+", "", text)
        return text

    @classmethod
    def _candidate_match_text(cls, candidate: PaperCandidate) -> str:
        parts = [
            candidate.title,
            candidate.abstract_text,
            candidate.assignee,
            candidate.inventor,
            candidate.publication_number,
            candidate.patent_id,
        ]
        return " ".join(cls._normalize_match_text(x) for x in parts if str(x or "").strip())

    @classmethod
    def _candidate_matches_keywords(cls, *, candidate: PaperCandidate, keywords: list[str], use_and: bool) -> bool:
        needles = [cls._normalize_match_text(k) for k in (keywords or []) if cls._normalize_match_text(k)]
        if not needles:
            return True
        haystack = cls._candidate_match_text(candidate)
        if not haystack:
            return False
        hits = [needle in haystack for needle in needles]
        return all(hits) if bool(use_and) else any(hits)

    @staticmethod
    def _build_source_stats(enabled: list[str], cfg: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "requested_limit": int(cfg.get(key, {}).get("limit", 30) or 30),
                "candidates": 0,
                "downloaded": 0,
                "reused": 0,
                "failed": 0,
                "skipped_keyword": 0,
                "skipped_duplicate": 0,
                "skipped_stopped": 0,
                "failed_reasons": {},
            }
            for key in enabled
        }

    @staticmethod
    def _translator_script_path() -> Path:
        return resolve_repo_path("tobeDeleted/translate_zh_to_en_example.py")

    @staticmethod
    def _parse_translator_output(stdout: str) -> str:
        en = ""
        for line in str(stdout or "").splitlines():
            s = str(line or "").strip()
            if s.upper().startswith("EN:"):
                en = s[3:].strip()
        return en

    def _translate_query_for_uspto(self, query: str) -> str:
        script = self._translator_script_path()
        if not script.exists():
            raise RuntimeError(f"translator_script_not_found: {script}")
        proc = subprocess.run(
            [sys.executable, str(script), str(query or "")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30,
            check=False,
        )
        if int(proc.returncode or 0) != 0:
            raise RuntimeError(f"translator_failed: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}")
        translated = self._parse_translator_output(proc.stdout)
        if not translated:
            raise RuntimeError(f"translator_empty_output: {proc.stdout.strip()}")
        return translated

    @staticmethod
    def _extract_completion_answer(payload: dict[str, Any] | None) -> str:
        def _walk(value: Any) -> str:
            if isinstance(value, str):
                s = value.strip()
                return s
            if isinstance(value, dict):
                for k in ("answer", "content", "text", "response", "message"):
                    if k in value:
                        got = _walk(value.get(k))
                        if got:
                            return got
                for k in ("data", "output", "result", "choices"):
                    if k in value:
                        got = _walk(value.get(k))
                        if got:
                            return got
                for v in value.values():
                    got = _walk(v)
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
    def _is_chat_method_unsupported_error(text: str) -> bool:
        lower = str(text or "").strip().lower()
        return "method chat not supported yet" in lower or "not supported yet" in lower

    def _resolve_general_llm_chat_ids(self) -> list[str]:
        chat_service = getattr(self.deps, "ragflow_chat_service", None)
        if chat_service is None:
            raise RuntimeError("ragflow_chat_service_not_available")
        forced_id = str(os.getenv("PAPER_ANALYSIS_CHAT_ID", "") or "").strip()
        if forced_id:
            return [forced_id]

        forced_name = str(os.getenv("PAPER_ANALYSIS_CHAT_NAME", "") or "").strip()
        preferred_names = [x for x in [forced_name, "[大模型]", "大模型", "[问题比对]", "问题比对", "[通用LLM]", "通用LLM", "小模型"] if x]

        try:
            all_chats = chat_service.list_chats(page_size=200)
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
                if normalized_name == normalized_target:
                    if cid not in ordered:
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
        raise RuntimeError(f"general_llm_chat_not_found; available_chats={names}")

    def _get_or_create_llm_session(
        self,
        *,
        actor: str,
        chat_id: str,
        force_new: bool = False,
        session_name: str | None = None,
    ) -> str:
        key = (str(actor), str(chat_id))
        if not force_new:
            with self._llm_lock:
                existing = self._llm_session_cache.get(key)
            if existing:
                return existing

        chat_service = getattr(self.deps, "ragflow_chat_service", None)
        if chat_service is None:
            raise RuntimeError("ragflow_chat_service_not_available")
        payload = chat_service._client.post_json_with_fallback(
            f"/api/v1/chats/{chat_id}/sessions",
            body={"name": str(session_name or f"paper-auto-analyze-{actor}")},
        )
        if not isinstance(payload, dict) or payload.get("code") != 0:
            raise RuntimeError(f"llm_session_create_failed: {payload}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"llm_session_create_invalid_data: {payload}")
        sid = str(data.get("id") or "").strip()
        if not sid:
            raise RuntimeError(f"llm_session_create_missing_id: {payload}")
        if not force_new:
            with self._llm_lock:
                self._llm_session_cache[key] = sid
        return sid

    def _ask_general_llm(self, *, actor: str, question: str, per_item_session_tag: str | None = None) -> str:
        chat_service = getattr(self.deps, "ragflow_chat_service", None)
        if chat_service is None:
            raise RuntimeError("ragflow_chat_service_not_available")
        last_error: Exception | None = None
        for chat_id in self._resolve_general_llm_chat_ids():
            try:
                session_id = self._get_or_create_llm_session(
                    actor=actor,
                    chat_id=chat_id,
                    force_new=True,
                    session_name=f"paper-auto-analyze-{actor}-{per_item_session_tag or uuid.uuid4().hex[:8]}",
                )
                payload = chat_service._client.post_json_with_fallback(
                    f"/api/v1/chats/{chat_id}/completions",
                    body={
                        "question": str(question or ""),
                        "session_id": session_id,
                        "stream": False,
                    },
                )
                if not isinstance(payload, dict) or payload.get("code") not in (0, None):
                    raise RuntimeError(f"llm_completion_failed: {payload}")
                answer = self._extract_completion_answer(payload)
                if not answer:
                    raise RuntimeError(f"llm_empty_answer: {payload}")
                answer_lower = str(answer).strip().lower()
                if answer_lower.startswith("**error**") or answer_lower.startswith("error:"):
                    if self._is_chat_method_unsupported_error(answer):
                        last_error = RuntimeError(f"llm_error_response: {answer}")
                        continue
                    raise RuntimeError(f"llm_error_response: {answer}")
                return answer
            except Exception as e:
                if self._is_chat_method_unsupported_error(str(e)):
                    last_error = e
                    continue
                raise
        if last_error is not None:
            raise RuntimeError(f"llm_all_candidates_failed: {last_error}")
        raise RuntimeError("llm_no_candidate_chat")

    def _build_analysis_prompt(self, *, item: Any) -> str:
        return (
            "你是论文分析助手。请根据以下论文信息，输出结构化分析，重点包括："
            "1) 论文关注点/研究问题；2) 内容大纲（3-6点）；3) 主要方法与关键结论；4) 创新点（2-5条）；"
            "5) 适用场景与局限（可选）。"
            "输出中文，条目化，避免空泛表述。\n\n"
            f"标题: {item.title or ''}\n"
            f"编号: {item.publication_number or ''}\n"
            f"发布日期: {item.publication_date or ''}\n"
            f"作者: {item.inventor or ''}\n"
            f"摘要: {item.abstract_text or ''}\n"
            f"详情链接: {item.detail_url or ''}\n"
            f"文件名: {item.filename or ''}\n"
        )

    def _analysis_txt_path(self, *, item: Any) -> Path:
        file_path = Path(str(item.file_path or ""))
        if file_path.exists() and file_path.is_file():
            return file_path.with_suffix(".analysis.txt")
        root = self._download_root() / str(item.session_id)
        root.mkdir(parents=True, exist_ok=True)
        return root / f"paper_{item.item_id}.analysis.txt"

    def _fetch_detail_page_text(self, detail_url: str) -> str:
        url = str(detail_url or "").strip()
        if not url:
            raise RuntimeError("detail_url_missing")
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._DOWNLOAD_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            raise RuntimeError(f"detail_page_fetch_failed: {e}") from e
        text = self._strip_html(raw)
        if not text:
            raise RuntimeError("detail_page_empty")
        return text[:12000]

    def _build_detail_fallback_prompt(self, *, item: Any, detail_text: str) -> str:
        return (
            "你是论文分析助手。PDF 不可用时，请基于网页文本输出结构化分析，重点包括："
            "1) 论文关注点/研究问题；2) 内容大纲（3-6点）；3) 主要方法与关键结论；4) 创新点（2-5条）；"
            "5) 适用场景与局限（可选）。"
            "输出中文，条目化，避免空泛表述。\n\n"
            f"标题: {item.title or ''}\n"
            f"编号: {item.publication_number or ''}\n"
            f"详情链接: {item.detail_url or ''}\n\n"
            "网页文本:\n"
            f"{detail_text}\n"
        )

    def _run_item_detail_auto_analysis(self, *, actor: str, item: Any) -> tuple[str | None, str | None]:
        detail_text = self._fetch_detail_page_text(str(getattr(item, "detail_url", "") or ""))
        question = self._build_detail_fallback_prompt(item=item, detail_text=detail_text)
        analysis_text = self._ask_general_llm(
            actor=actor,
            question=question,
            per_item_session_tag=f"s{getattr(item, 'session_id', '')}-i{getattr(item, 'item_id', 0)}-detail",
        )
        txt_path = self._analysis_txt_path(item=item)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(analysis_text, encoding="utf-8")
        return analysis_text, str(txt_path)

    def _run_item_auto_analysis(self, *, actor: str, item: Any) -> tuple[str | None, str | None]:
        if not self._is_downloaded_status(getattr(item, "status", None)):
            return None, None
        if not str(getattr(item, "file_path", "") or "").strip():
            return None, None
        question = self._build_analysis_prompt(item=item)
        analysis_text = self._ask_general_llm(
            actor=actor,
            question=question,
            per_item_session_tag=f"s{getattr(item, 'session_id', '')}-i{getattr(item, 'item_id', 0)}",
        )
        txt_path = self._analysis_txt_path(item=item)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(analysis_text, encoding="utf-8")
        return analysis_text, str(txt_path)

    def _build_item_row(self, *, source_key: str, source_index: int, candidate: PaperCandidate, session_dir: Path) -> dict[str, Any]:
        safe_title = self._strip_html(candidate.title)
        safe_abstract = self._strip_html(candidate.abstract_text)
        preferred_name = str(candidate.publication_number or "").strip() or safe_title or f"{source_key}_{source_index}"
        filename = self._safe_filename(preferred_name, fallback=f"{source_key}_{source_index}")
        source_dir = session_dir / source_key
        source_dir.mkdir(parents=True, exist_ok=True)
        local_path = source_dir / filename

        status = "downloaded"
        error = None
        file_size: int | None = None
        mime_type = self._MIME_TYPE_DEFAULT
        if not candidate.pdf_url:
            status = "failed"
            error = "missing_pdf_url"
        else:
            try:
                content = self._download_pdf_bytes(candidate.pdf_url)
                local_path.write_bytes(content)
                file_size = len(content)
            except Exception as e:
                status = "failed"
                error = f"download_failed: {e}"
                if local_path.exists():
                    try:
                        local_path.unlink()
                    except Exception:
                        pass

        return {
            "source": candidate.source,
            "source_label": candidate.source_label,
            "patent_id": candidate.patent_id,
            "title": safe_title,
            "abstract_text": safe_abstract,
            "publication_number": candidate.publication_number,
            "publication_date": candidate.publication_date,
            "inventor": candidate.inventor,
            "assignee": candidate.assignee,
            "detail_url": candidate.detail_url,
            "pdf_url": candidate.pdf_url,
            "file_path": str(local_path) if status == "downloaded" else None,
            "filename": filename,
            "file_size": file_size,
            "mime_type": mime_type if status == "downloaded" else None,
            "status": status,
            "error": error,
        }

    @classmethod
    def _register_job(cls, session_id: str, job: threading.Thread) -> None:
        with cls._jobs_lock:
            cls._jobs[session_id] = job
            cls._cancelled_sessions.discard(session_id)
            cls._stop_requested_sessions.discard(session_id)

    @classmethod
    def _cancel_job(cls, session_id: str) -> threading.Thread | None:
        with cls._jobs_lock:
            cls._cancelled_sessions.add(session_id)
            return cls._jobs.get(session_id)

    @classmethod
    def _is_cancelled(cls, session_id: str) -> bool:
        with cls._jobs_lock:
            return session_id in cls._cancelled_sessions

    @classmethod
    def _request_stop(cls, session_id: str) -> threading.Thread | None:
        with cls._jobs_lock:
            cls._stop_requested_sessions.add(session_id)
            return cls._jobs.get(session_id)

    @classmethod
    def _is_stop_requested(cls, session_id: str) -> bool:
        with cls._jobs_lock:
            return session_id in cls._stop_requested_sessions

    @classmethod
    def _finish_job(cls, session_id: str) -> None:
        with cls._jobs_lock:
            cls._jobs.pop(session_id, None)
            cls._cancelled_sessions.discard(session_id)
            cls._stop_requested_sessions.discard(session_id)

    def _run_download_job(
        self,
        *,
        session_id: str,
        actor: str,
        query: str,
        keywords: list[str],
        use_and: bool,
        source_queries: dict[str, str],
        source_errors_seed: dict[str, str],
        auto_analyze: bool,
        enabled_sources: list[str],
        source_cfg: dict[str, dict[str, Any]],
    ) -> None:
        source_errors: dict[str, str] = dict(source_errors_seed or {})
        source_stats = self._build_source_stats(enabled_sources, source_cfg)
        queues: dict[str, deque[tuple[int, PaperCandidate]]] = {}
        seen: set[str] = set()
        session_dir = self._session_dir(actor_id=actor, session_id=session_id)

        def _inc_failed_reason(source_key: str, reason: str) -> None:
            stats = source_stats.get(source_key, {})
            fr = stats.get("failed_reasons")
            if not isinstance(fr, dict):
                fr = {}
                stats["failed_reasons"] = fr
            k = str(reason or "unknown_failed_reason")
            fr[k] = int(fr.get(k, 0) or 0) + 1

        def _mark_stopped() -> None:
            for key in enabled_sources:
                q = queues.get(key)
                if q:
                    source_stats[key]["skipped_stopped"] = int(source_stats[key].get("skipped_stopped", 0) or 0) + len(q)
            self.store.update_session_runtime(
                session_id=session_id,
                status="stopped",
                source_errors=source_errors,
                source_stats=source_stats,
            )

        for key in enabled_sources:
            source_stats[key]["query"] = str(source_queries.get(key) or query or "")

        try:
            for source_key in enabled_sources:
                if self._is_cancelled(session_id):
                    return
                if self._is_stop_requested(session_id):
                    _mark_stopped()
                    return
                provider = self._sources.get(source_key)
                if provider is None:
                    source_errors[source_key] = "source_not_implemented"
                    self.store.update_session_runtime(session_id=session_id, status="running", source_errors=source_errors, source_stats=source_stats)
                    continue
                limit = int(source_cfg.get(source_key, {}).get("limit", 30) or 30)
                source_query = str(source_queries.get(source_key) or query or "").strip()
                source_stats[source_key]["query"] = source_query
                try:
                    raw = provider.search(query=source_query, limit=limit)
                except PaperSourceError as e:
                    source_errors[source_key] = str(e)
                    self.store.update_session_runtime(session_id=session_id, status="running", source_errors=source_errors, source_stats=source_stats)
                    continue
                except Exception as e:
                    source_errors[source_key] = f"source_failed: {e}"
                    self.store.update_session_runtime(session_id=session_id, status="running", source_errors=source_errors, source_stats=source_stats)
                    continue

                raw_candidates: list[tuple[int, PaperCandidate]] = [
                    (idx + 1, c) for idx, c in enumerate(raw or []) if isinstance(c, PaperCandidate)
                ]
                source_stats[source_key]["candidates"] = len(raw_candidates)
                typed: list[tuple[int, PaperCandidate]] = []
                for idx, c in enumerate(raw or []):
                    if not isinstance(c, PaperCandidate):
                        continue
                    if not self._candidate_matches_keywords(
                        candidate=c,
                        keywords=keywords,
                        use_and=use_and,
                    ):
                        source_stats[source_key]["skipped_keyword"] = int(source_stats[source_key].get("skipped_keyword", 0) or 0) + 1
                        continue
                    typed.append((idx + 1, c))
                if not typed:
                    source_errors.setdefault(source_key, "no_results")
                queues[source_key] = deque(typed)
                self.store.update_session_runtime(session_id=session_id, status="running", source_errors=source_errors, source_stats=source_stats)

            while True:
                if self._is_cancelled(session_id):
                    return
                if self._is_stop_requested(session_id):
                    _mark_stopped()
                    return
                progressed = False
                for source_key in enabled_sources:
                    queue = queues.get(source_key)
                    if not queue:
                        continue
                    while queue:
                        if self._is_cancelled(session_id):
                            return
                        if self._is_stop_requested(session_id):
                            _mark_stopped()
                            return
                        source_index, candidate = queue.popleft()
                        key = self._item_key(candidate)
                        if key and key in seen:
                            source_stats[source_key]["skipped_duplicate"] = int(source_stats[source_key].get("skipped_duplicate", 0) or 0) + 1
                            continue
                        if key:
                            seen.add(key)
                        reused = self.store.find_reusable_download(
                            created_by=actor,
                            patent_id=candidate.patent_id,
                            publication_number=candidate.publication_number,
                            title=self._strip_html(candidate.title),
                        )
                        if reused and str(reused.file_path or "").strip() and os.path.exists(str(reused.file_path)):
                            row = {
                                "source": candidate.source,
                                "source_label": candidate.source_label,
                                "patent_id": candidate.patent_id,
                                "title": self._strip_html(candidate.title),
                                "abstract_text": self._strip_html(candidate.abstract_text),
                                "publication_number": candidate.publication_number,
                                "publication_date": candidate.publication_date,
                                "inventor": candidate.inventor,
                                "assignee": candidate.assignee,
                                "detail_url": candidate.detail_url,
                                "pdf_url": candidate.pdf_url,
                                "file_path": reused.file_path,
                                "filename": reused.filename or self._safe_filename(
                                    str(candidate.publication_number or candidate.title or f"{source_key}_{source_index}"),
                                    fallback=f"{source_key}_{source_index}",
                                ),
                                "file_size": reused.file_size,
                                "mime_type": reused.mime_type or self._MIME_TYPE_DEFAULT,
                                "status": "downloaded_cached",
                                "error": None,
                                "analysis_text": reused.analysis_text,
                                "analysis_file_path": reused.analysis_file_path,
                            }
                            source_stats[source_key]["reused"] += 1
                        else:
                            row = self._build_item_row(
                                source_key=source_key,
                                source_index=source_index,
                                candidate=candidate,
                                session_dir=session_dir,
                            )

                        if self._is_downloaded_status(row.get("status")):
                            source_stats[source_key]["downloaded"] += 1
                        else:
                            source_stats[source_key]["failed"] += 1
                            err = str(row.get("error") or "").strip()
                            if err.startswith("download_failed:"):
                                _inc_failed_reason(source_key, "download_failed")
                            elif err == "missing_pdf_url":
                                _inc_failed_reason(source_key, "missing_pdf_url")
                            elif err:
                                _inc_failed_reason(source_key, err[:120])
                            else:
                                _inc_failed_reason(source_key, "unknown_failed_reason")
                        created_item = self.store.create_item(session_id=session_id, item=row)
                        if bool(auto_analyze) and not str(created_item.analysis_text or "").strip():
                            should_analyze_pdf = self._is_downloaded_status(created_item.status)
                            should_analyze_detail = (
                                str(created_item.status or "") == "failed"
                                and (
                                    str(created_item.error or "") == "missing_pdf_url"
                                    or str(created_item.error or "").startswith("download_failed:")
                                )
                            )
                            if should_analyze_pdf or should_analyze_detail:
                                try:
                                    if should_analyze_pdf:
                                        analysis_text, analysis_path = self._run_item_auto_analysis(actor=actor, item=created_item)
                                    else:
                                        analysis_text, analysis_path = self._run_item_detail_auto_analysis(actor=actor, item=created_item)
                                    created_item = self.store.update_item_analysis(
                                        session_id=session_id,
                                        item_id=created_item.item_id,
                                        analysis_text=analysis_text,
                                        analysis_file_path=analysis_path,
                                    ) or created_item
                                except Exception as analysis_error:
                                    msg = f"auto_analyze_failed: {analysis_error}"
                                    source_errors[source_key] = msg
                                    self.store.update_item_analysis(
                                        session_id=session_id,
                                        item_id=created_item.item_id,
                                        analysis_text=f"自动分析失败：{analysis_error}",
                                        analysis_file_path=None,
                                    )
                        self.store.update_session_runtime(session_id=session_id, status="running", source_errors=source_errors, source_stats=source_stats)
                        progressed = True
                        break
                if not progressed:
                    break

            self.store.update_session_runtime(session_id=session_id, status="completed", source_errors=source_errors, source_stats=source_stats)
        except Exception as e:
            self.store.update_session_runtime(
                session_id=session_id,
                status="failed",
                error=f"download_job_failed: {e}",
                source_errors=source_errors,
                source_stats=source_stats,
            )
        finally:
            self._finish_job(session_id)

    def stop_session_download(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="paper_session_not_found")
        self._assert_session_access(session, ctx)

        status = str(getattr(session, "status", "") or "")
        if status in {"completed", "failed", "stopped"}:
            return {"ok": True, "already_finished": True, "status": status, "session_id": session_id}

        job = self._request_stop(session_id)
        if job is not None and job.is_alive():
            self.store.update_session_runtime(session_id=session_id, status="stopping")
            return {"ok": True, "already_finished": False, "status": "stopping", "session_id": session_id}

        self.store.update_session_runtime(session_id=session_id, status="stopped")
        return {"ok": True, "already_finished": False, "status": "stopped", "session_id": session_id}

    def _assert_session_access(self, session: Any, ctx: Any) -> None:
        if bool(getattr(ctx.snapshot, "is_admin", False)):
            return
        if str(getattr(session, "created_by", "")) != str(ctx.payload.sub):
            raise HTTPException(status_code=403, detail="paper_session_not_allowed")

    def _resolve_session_and_item(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[Any, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="paper_session_not_found")
        self._assert_session_access(session, ctx)
        item = self.store.get_item(session_id=session_id, item_id=item_id)
        if not item:
            raise HTTPException(status_code=404, detail="paper_item_not_found")
        return session, item

    def _ensure_file_bytes(self, *, file_path: str | None, filename: str | None) -> bytes:
        path = Path(str(file_path or ""))
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail=f"paper_file_not_found: {filename or ''}")
        try:
            return path.read_bytes()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"paper_file_read_failed: {e}") from e

    def create_session_and_download(
        self,
        *,
        ctx: Any,
        keyword_text: str,
        use_and: bool,
        auto_analyze: bool,
        source_configs: dict[str, Any] | None,
    ) -> dict[str, Any]:
        keywords = self.parse_keywords(keyword_text)
        if not keywords:
            raise HTTPException(status_code=400, detail="keyword_required")

        normalized_sources = self._normalize_source_configs(source_configs)
        enabled_sources = [k for k in self._SOURCE_ORDER if normalized_sources.get(k, {}).get("enabled")]
        if not enabled_sources:
            raise HTTPException(status_code=400, detail="source_required")

        query = self._build_query(keywords, use_and)
        quoted_query = self._build_quoted_query(keywords, use_and)
        source_queries: dict[str, str] = {key: (quoted_query or query) for key in enabled_sources}
        source_errors_seed: dict[str, str] = {}

        source_stats = self._build_source_stats(enabled_sources, normalized_sources)
        for key in enabled_sources:
            source_stats[key]["query"] = str(source_queries.get(key) or "")

        session_id = str(uuid.uuid4())
        actor = str(ctx.payload.sub)
        session = self.store.create_session(
            session_id=session_id,
            created_by=actor,
            keyword_text=keyword_text,
            keywords=keywords,
            use_and=bool(use_and),
            sources=normalized_sources,
            created_at_ms=int(time.time() * 1000),
            status="running",
            source_errors=source_errors_seed,
            source_stats=source_stats,
        )

        worker = threading.Thread(
            target=self._run_download_job,
            kwargs={
                "session_id": session_id,
                "actor": actor,
                "query": query,
                "keywords": keywords,
                "use_and": bool(use_and),
                "source_queries": source_queries,
                "source_errors_seed": source_errors_seed,
                "auto_analyze": bool(auto_analyze),
                "enabled_sources": enabled_sources,
                "source_cfg": normalized_sources,
            },
            daemon=True,
            name=f"paper-download-{session_id[:8]}",
        )
        self._register_job(session_id, worker)
        worker.start()

        session_data = session_to_dict(session)
        return {
            "session": session_data,
            "items": [],
            "source_errors": session_data.get("source_errors") or {},
            "source_stats": session_data.get("source_stats") or {},
            "summary": {
                "status": "running",
                "total": 0,
                "downloaded": 0,
                "failed": 0,
                "added": 0,
                "auto_analyze": bool(auto_analyze),
                "enabled_sources": len(enabled_sources),
            },
        }
    @staticmethod
    def _build_summary(items: list[Any], status: str | None) -> dict[str, Any]:
        return {
            "status": str(status or ""),
            "total": len(items),
            "downloaded": sum(1 for i in items if PaperDownloadManager._is_downloaded_status(i.status)),
            "failed": sum(1 for i in items if not PaperDownloadManager._is_downloaded_status(i.status)),
            "added": sum(1 for i in items if bool(i.added_doc_id)),
            "analyzed": sum(1 for i in items if bool(getattr(i, "analysis_text", None))),
        }

    def get_session_payload(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="paper_session_not_found")
        self._assert_session_access(session, ctx)
        items = self.store.list_items(session_id=session_id)
        session_data = session_to_dict(session)
        return {
            "session": session_data,
            "items": [self._serialize_item(i) for i in items],
            "source_errors": session_data.get("source_errors") or {},
            "source_stats": session_data.get("source_stats") or {},
            "summary": self._build_summary(items, getattr(session, "status", "")),
        }

    @staticmethod
    def _history_group_from_session(session: Any) -> tuple[str, list[str], bool]:
        keywords: list[str] = []
        try:
            raw = json.loads(str(getattr(session, "keywords_json", "") or "[]"))
            if isinstance(raw, list):
                for v in raw:
                    s = str(v or "").strip()
                    if s:
                        keywords.append(s)
        except Exception:
            keywords = []
        use_and = bool(getattr(session, "use_and", False))
        normalized = sorted({k.lower() for k in keywords if k.strip()})
        group_key = f"{'and' if use_and else 'or'}::{ '|'.join(normalized)}"
        return group_key, keywords, use_and

    @staticmethod
    def _history_item_key(item: Any) -> str:
        for v in (getattr(item, "patent_id", None), getattr(item, "publication_number", None), getattr(item, "title", None)):
            s = str(v or "").strip().lower()
            if s:
                return s
        return f"session:{getattr(item, 'session_id', '')}:item:{getattr(item, 'item_id', 0)}"

    @staticmethod
    def _has_effective_analysis_text(text: str | None) -> bool:
        s = str(text or "").strip()
        if not s:
            return False
        s_l = s.lower()
        if s.startswith("自动分析失败："):
            return False
        if s_l.startswith("**error**") or s_l.startswith("error:") or "llm_error_response" in s_l:
            return False
        return True

    def list_history_keywords(self, *, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self.store.list_sessions_by_creator(created_by=actor, limit=1000)
        grouped: dict[str, dict[str, Any]] = {}
        grouped_sessions: dict[str, list[Any]] = {}
        for s in sessions:
            key, keywords, use_and = self._history_group_from_session(s)
            if not keywords:
                continue
            grouped_sessions.setdefault(key, []).append(s)
            node = grouped.get(key)
            if not node:
                node = {
                    "history_key": key,
                    "keywords": keywords,
                    "use_and": bool(use_and),
                    "keyword_display": f" {'AND' if use_and else 'OR'} ".join(keywords),
                    "latest_session_id": s.session_id,
                    "latest_at_ms": int(s.created_at_ms),
                    "session_count": 0,
                }
                grouped[key] = node
            node["session_count"] = int(node["session_count"]) + 1
            if int(s.created_at_ms) >= int(node["latest_at_ms"]):
                node["latest_at_ms"] = int(s.created_at_ms)
                node["latest_session_id"] = s.session_id

        for key, node in grouped.items():
            merged: dict[str, Any] = {}
            for s in sorted(grouped_sessions.get(key, []), key=lambda x: int(x.created_at_ms), reverse=True):
                for item in self.store.list_items(session_id=s.session_id):
                    k = self._history_item_key(item)
                    existing = merged.get(k)
                    if existing is None or int(getattr(item, "created_at_ms", 0) or 0) >= int(getattr(existing, "created_at_ms", 0) or 0):
                        merged[k] = item
            merged_items = list(merged.values())
            downloaded_count = sum(1 for i in merged_items if self._is_downloaded_status(getattr(i, "status", None)))
            analyzed_count = sum(1 for i in merged_items if self._has_effective_analysis_text(getattr(i, "analysis_text", None)))
            added_count = sum(1 for i in merged_items if bool(getattr(i, "added_doc_id", None)))
            node["downloaded_count"] = int(downloaded_count)
            node["analyzed_count"] = int(analyzed_count)
            node["added_count"] = int(added_count)

        history = sorted(grouped.values(), key=lambda x: int(x.get("latest_at_ms", 0)), reverse=True)
        return {"history": history, "count": len(history)}

    def get_history_group_payload(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self.store.list_sessions_by_creator(created_by=actor, limit=1000)
        target_sessions: list[Any] = []
        target_meta: dict[str, Any] | None = None
        for s in sessions:
            key, keywords, use_and = self._history_group_from_session(s)
            if key != str(history_key):
                continue
            target_sessions.append(s)
            if target_meta is None or int(s.created_at_ms) >= int(target_meta.get("latest_at_ms", 0)):
                target_meta = {
                    "history_key": key,
                    "keywords": keywords,
                    "use_and": bool(use_and),
                    "keyword_display": f" {'AND' if use_and else 'OR'} ".join(keywords),
                    "latest_session_id": s.session_id,
                    "latest_at_ms": int(s.created_at_ms),
                }
        if not target_sessions:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        merged: dict[str, Any] = {}
        for s in sorted(target_sessions, key=lambda x: int(x.created_at_ms), reverse=True):
            for item in self.store.list_items(session_id=s.session_id):
                k = self._history_item_key(item)
                existing = merged.get(k)
                if existing is None or int(getattr(item, "created_at_ms", 0) or 0) >= int(getattr(existing, "created_at_ms", 0) or 0):
                    merged[k] = item

        merged_items = sorted(merged.values(), key=lambda x: int(getattr(x, "created_at_ms", 0) or 0), reverse=True)
        return {
            "history": {
                **(target_meta or {}),
                "session_count": len(target_sessions),
                "item_count": len(merged_items),
            },
            "items": [self._serialize_item(i) for i in merged_items],
            "summary": {
                "total": len(merged_items),
                "downloaded": sum(1 for i in merged_items if self._is_downloaded_status(getattr(i, "status", None))),
                "failed": sum(1 for i in merged_items if not self._is_downloaded_status(getattr(i, "status", None))),
            },
        }

    def delete_history_group(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self.store.list_sessions_by_creator(created_by=actor, limit=1000)
        target_session_ids: list[str] = []
        for s in sessions:
            key, _, _ = self._history_group_from_session(s)
            if key == str(history_key):
                target_session_ids.append(str(s.session_id))
        if not target_session_ids:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        deleted_sessions = 0
        deleted_items = 0
        deleted_files = 0
        errors: list[dict[str, Any]] = []
        for sid in target_session_ids:
            try:
                res = self.delete_session(session_id=sid, ctx=ctx, delete_local_kb=False)
                deleted_sessions += 1
                deleted_items += int(res.get("deleted_items", 0) or 0)
                deleted_files += int(res.get("deleted_files", 0) or 0)
            except Exception as e:
                errors.append({"session_id": sid, "error": str(e)})

        return {
            "ok": True,
            "history_key": str(history_key),
            "deleted_sessions": deleted_sessions,
            "deleted_items": deleted_items,
            "deleted_files": deleted_files,
            "errors": errors,
        }

    def add_history_group_to_local_kb(self, *, history_key: str, ctx: Any, kb_ref: str = LOCAL_PAPERS_KB_REF) -> dict[str, Any]:
        actor = str(ctx.payload.sub)
        sessions = self.store.list_sessions_by_creator(created_by=actor, limit=1000)
        target_sessions: list[Any] = []
        for s in sessions:
            key, _, _ = self._history_group_from_session(s)
            if key == str(history_key):
                target_sessions.append(s)
        if not target_sessions:
            raise HTTPException(status_code=404, detail="history_keyword_not_found")

        merged: dict[str, Any] = {}
        for s in sorted(target_sessions, key=lambda x: int(x.created_at_ms), reverse=True):
            for item in self.store.list_items(session_id=s.session_id):
                k = self._history_item_key(item)
                existing = merged.get(k)
                if existing is None or int(getattr(item, "created_at_ms", 0) or 0) >= int(getattr(existing, "created_at_ms", 0) or 0):
                    merged[k] = item

        success = 0
        failed = 0
        skipped = 0
        details: list[dict[str, Any]] = []
        for item in merged.values():
            if not self._is_downloaded_status(getattr(item, "status", None)):
                skipped += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": False, "skipped": True, "reason": "not_downloaded"})
                continue
            if getattr(item, "added_doc_id", None):
                skipped += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": True, "already_added": True})
                continue
            try:
                self.add_item_to_local_kb(
                    session_id=str(item.session_id),
                    item_id=int(item.item_id),
                    ctx=ctx,
                    kb_ref=kb_ref,
                    from_batch=True,
                )
                success += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": True})
            except Exception as e:
                failed += 1
                details.append({"session_id": item.session_id, "item_id": int(item.item_id), "ok": False, "error": str(e)})

        return {
            "ok": True,
            "history_key": str(history_key),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "items": details,
        }

    def get_item_preview_payload(self, *, session_id: str, item_id: int, ctx: Any, render: str = "default") -> dict[str, Any]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        return build_preview_payload(content, item.filename or f"paper_{item_id}.pdf", doc_id=str(item_id), render=render)

    def get_item_download_payload(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[bytes, str, str]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        filename = item.filename or f"paper_{item_id}.pdf"
        mime_type = item.mime_type or self._MIME_TYPE_DEFAULT
        return content, filename, mime_type

    def _upload_blob_to_kb(
        self,
        *,
        ctx: Any,
        kb_ref: str,
        filename: str,
        content: bytes,
        mime_type: str,
        review_notes: str,
    ) -> Any:
        deps = self.deps
        kb_info = resolve_kb_ref(deps, kb_ref)
        uploads_dir = resolve_repo_path(settings.UPLOAD_DIR)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        staged_filename = f"{uuid.uuid4()}_{filename}"
        staged_path = uploads_dir / staged_filename
        staged_path.write_bytes(content)

        doc = None
        try:
            doc = deps.kb_store.create_document(
                filename=filename,
                file_path=str(staged_path),
                file_size=len(content),
                mime_type=mime_type,
                uploaded_by=ctx.payload.sub,
                kb_id=(kb_info.dataset_id or kb_ref),
                kb_dataset_id=kb_info.dataset_id,
                kb_name=(kb_info.name or kb_ref),
                status="pending",
            )

            kb_targets = self._kb_target_candidates(kb_ref, kb_info)
            ragflow_doc_id = None
            selected_target = None
            for target in kb_targets:
                try:
                    ragflow_doc_id = deps.ragflow_service.upload_document_blob(
                        file_filename=doc.filename,
                        file_content=content,
                        kb_id=target,
                    )
                except Exception:
                    ragflow_doc_id = None
                if ragflow_doc_id:
                    selected_target = target
                    break
            if not ragflow_doc_id:
                raise HTTPException(
                    status_code=502,
                    detail=f"upload_to_ragflow_failed: kb_ref={kb_ref}, targets={','.join(kb_targets)}",
                )

            selected_kb_info = resolve_kb_ref(deps, selected_target or kb_ref)
            dataset_ref = selected_kb_info.dataset_id or selected_target or kb_ref
            if ragflow_doc_id != "uploaded":
                try:
                    deps.ragflow_service.parse_document(dataset_ref=dataset_ref, document_id=ragflow_doc_id)
                except Exception:
                    pass

            updated = deps.kb_store.update_document_status(
                doc_id=doc.doc_id,
                status="approved",
                reviewed_by=ctx.payload.sub,
                review_notes=review_notes,
                ragflow_doc_id=ragflow_doc_id,
            )
            if not updated:
                raise RuntimeError("kb_status_update_failed")
            return updated
        except Exception:
            if doc is not None:
                try:
                    deps.kb_store.delete_document(doc.doc_id)
                except Exception:
                    pass
            try:
                if staged_path.exists():
                    staged_path.unlink()
            except Exception:
                pass
            raise

    def add_item_to_local_kb(
        self,
        *,
        session_id: str,
        item_id: int,
        ctx: Any,
        kb_ref: str = LOCAL_PAPERS_KB_REF,
        from_batch: bool = False,
    ) -> dict[str, Any]:
        deps = self.deps
        assert_can_upload(ctx.snapshot)
        assert_kb_allowed(ctx.snapshot, kb_ref)

        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        existing_doc = deps.kb_store.get_document(item.added_doc_id) if item.added_doc_id else None
        if existing_doc:
            if item.added_analysis_doc_id or not str(item.analysis_file_path or "").strip():
                return {
                    "item": self._serialize_item(item),
                    "document": {
                        "doc_id": existing_doc.doc_id,
                        "filename": existing_doc.filename,
                        "kb_id": existing_doc.kb_id,
                        "ragflow_doc_id": existing_doc.ragflow_doc_id,
                        "status": existing_doc.status,
                    },
                    "already_added": True,
                }

        try:
            if existing_doc is not None:
                updated = existing_doc
            else:
                content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
                updated = self._upload_blob_to_kb(
                    ctx=ctx,
                    kb_ref=kb_ref,
                    filename=(item.filename or f"paper_{item_id}.pdf"),
                    content=content,
                    mime_type=(item.mime_type or self._MIME_TYPE_DEFAULT),
                    review_notes="added_from_paper_download",
                )

            analysis_doc_id = item.added_analysis_doc_id
            analysis_path = str(item.analysis_file_path or "").strip()
            if analysis_path and not analysis_doc_id:
                analysis_file = Path(analysis_path)
                if analysis_file.exists() and analysis_file.is_file():
                    analysis_content = analysis_file.read_bytes()
                    analysis_name = analysis_file.name or f"{Path(item.filename or f'paper_{item_id}.pdf').stem}.analysis.txt"
                    analysis_doc = self._upload_blob_to_kb(
                        ctx=ctx,
                        kb_ref=kb_ref,
                        filename=analysis_name,
                        content=analysis_content,
                        mime_type="text/plain; charset=utf-8",
                        review_notes="added_paper_analysis_from_paper_download",
                    )
                    analysis_doc_id = analysis_doc.doc_id

            marked = self.store.mark_item_added(
                session_id=session_id,
                item_id=item_id,
                added_doc_id=updated.doc_id,
                added_analysis_doc_id=analysis_doc_id,
                ragflow_doc_id=updated.ragflow_doc_id,
            )
            if not marked:
                raise RuntimeError("mark_item_added_failed")

            audit = getattr(deps, "audit_log_store", None)
            if audit:
                try:
                    audit.log_event(
                        action="paper_kb_add",
                        actor=ctx.payload.sub,
                        source="paper_download",
                        doc_id=updated.doc_id,
                        filename=updated.filename,
                        kb_id=(updated.kb_name or updated.kb_id),
                        kb_dataset_id=getattr(updated, "kb_dataset_id", None),
                        kb_name=getattr(updated, "kb_name", None) or (updated.kb_name or updated.kb_id),
                        meta={
                            "session_id": session_id,
                            "item_id": int(item_id),
                            "paper_source": item.source,
                            "paper_id": item.patent_id,
                            "batch": bool(from_batch),
                            "kb_ref": kb_ref,
                        },
                        **actor_fields_from_ctx(deps, ctx),
                    )
                except Exception:
                    pass

            return {
                "item": self._serialize_item(marked),
                "document": {
                    "doc_id": updated.doc_id,
                    "filename": updated.filename,
                    "kb_id": (updated.kb_name or updated.kb_id),
                    "ragflow_doc_id": updated.ragflow_doc_id,
                    "status": updated.status,
                },
                "already_added": False,
            }
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"paper_add_to_kb_failed: {e}") from e

    def add_all_to_local_kb(
        self,
        *,
        session_id: str,
        ctx: Any,
        kb_ref: str = LOCAL_PAPERS_KB_REF,
    ) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="paper_session_not_found")
        self._assert_session_access(session, ctx)

        items = self.store.list_items(session_id=session_id)
        success = 0
        failed = 0
        details: list[dict[str, Any]] = []
        for item in items:
            if not self._is_downloaded_status(item.status):
                continue
            if item.added_doc_id:
                details.append({"item_id": item.item_id, "ok": True, "already_added": True})
                continue
            try:
                self.add_item_to_local_kb(session_id=session_id, item_id=item.item_id, ctx=ctx, kb_ref=kb_ref, from_batch=True)
                success += 1
                details.append({"item_id": item.item_id, "ok": True})
            except Exception as e:
                failed += 1
                details.append({"item_id": item.item_id, "ok": False, "error": str(e)})

        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="paper_kb_add_all",
                    actor=ctx.payload.sub,
                    source="paper_download",
                    meta={"session_id": session_id, "kb_ref": kb_ref, "success": success, "failed": failed},
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        return {
            "success": success,
            "failed": failed,
            "items": details,
            "session": self.get_session_payload(session_id=session_id, ctx=ctx),
        }
    def delete_item(self, *, session_id: str, item_id: int, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        deleted_file = False
        deleted_analysis_file = False
        deleted_doc = False
        deleted_analysis_doc = False

        if delete_local_kb and item.added_doc_id:
            assert_can_delete(ctx.snapshot)
            doc = self.deps.kb_store.get_document(item.added_doc_id)
            if doc:
                assert_kb_allowed(ctx.snapshot, doc.kb_id)
                DocumentManager(self.deps).delete_knowledge_document(doc_id=doc.doc_id, ctx=ctx)
                deleted_doc = True
        if delete_local_kb and item.added_analysis_doc_id:
            assert_can_delete(ctx.snapshot)
            analysis_doc = self.deps.kb_store.get_document(item.added_analysis_doc_id)
            if analysis_doc:
                assert_kb_allowed(ctx.snapshot, analysis_doc.kb_id)
                DocumentManager(self.deps).delete_knowledge_document(doc_id=analysis_doc.doc_id, ctx=ctx)
                deleted_analysis_doc = True

        path_text = str(item.file_path or "").strip()
        if path_text:
            p = Path(path_text)
            if p.exists():
                try:
                    p.unlink()
                    deleted_file = True
                except Exception:
                    pass
        analysis_path_text = str(item.analysis_file_path or "").strip()
        if analysis_path_text:
            ap = Path(analysis_path_text)
            if ap.exists():
                try:
                    ap.unlink()
                    deleted_analysis_file = True
                except Exception:
                    pass

        deleted = self.store.delete_item(session_id=session_id, item_id=item_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="paper_item_not_found")

        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="paper_item_delete",
                    actor=ctx.payload.sub,
                    source="paper_download",
                    meta={
                        "session_id": session_id,
                        "item_id": int(item_id),
                        "deleted_file": bool(deleted_file),
                        "deleted_analysis_file": bool(deleted_analysis_file),
                        "deleted_doc": bool(deleted_doc),
                        "deleted_analysis_doc": bool(deleted_analysis_doc),
                        "delete_local_kb": bool(delete_local_kb),
                    },
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        return {
            "ok": True,
            "item_id": int(item_id),
            "deleted_file": bool(deleted_file),
            "deleted_analysis_file": bool(deleted_analysis_file),
            "deleted_doc": bool(deleted_doc),
            "deleted_analysis_doc": bool(deleted_analysis_doc),
        }

    def delete_session(self, *, session_id: str, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="paper_session_not_found")
        self._assert_session_access(session, ctx)

        job = self._cancel_job(session_id)
        if job and job.is_alive():
            job.join(timeout=2.0)

        items = self.store.list_items(session_id=session_id)
        deleted_files = 0
        deleted_docs = 0
        doc_errors: list[dict[str, Any]] = []

        if delete_local_kb:
            assert_can_delete(ctx.snapshot)
            mgr = DocumentManager(self.deps)
            for item in items:
                if not item.added_doc_id:
                    pass
                else:
                    doc = self.deps.kb_store.get_document(item.added_doc_id)
                    if doc:
                        try:
                            assert_kb_allowed(ctx.snapshot, doc.kb_id)
                            mgr.delete_knowledge_document(doc_id=doc.doc_id, ctx=ctx)
                            deleted_docs += 1
                        except Exception as e:
                            doc_errors.append({"item_id": item.item_id, "doc_id": doc.doc_id, "error": str(e)})
                if item.added_analysis_doc_id:
                    analysis_doc = self.deps.kb_store.get_document(item.added_analysis_doc_id)
                    if analysis_doc:
                        try:
                            assert_kb_allowed(ctx.snapshot, analysis_doc.kb_id)
                            mgr.delete_knowledge_document(doc_id=analysis_doc.doc_id, ctx=ctx)
                            deleted_docs += 1
                        except Exception as e:
                            doc_errors.append({"item_id": item.item_id, "doc_id": analysis_doc.doc_id, "error": str(e)})

        for item in items:
            path_text = str(item.file_path or "").strip()
            if not path_text:
                continue
            p = Path(path_text)
            if not p.exists():
                continue
            try:
                p.unlink()
                deleted_files += 1
            except Exception:
                pass
            analysis_path_text = str(item.analysis_file_path or "").strip()
            if analysis_path_text:
                ap = Path(analysis_path_text)
                if ap.exists():
                    try:
                        ap.unlink()
                        deleted_files += 1
                    except Exception:
                        pass

        try:
            root = self._download_root() / str(session.created_by) / session_id
            if root.exists():
                for p in sorted(root.rglob("*"), reverse=True):
                    if p.is_file():
                        continue
                    try:
                        p.rmdir()
                    except Exception:
                        pass
                try:
                    root.rmdir()
                except Exception:
                    pass
        except Exception:
            pass

        store_result = self.store.delete_session(session_id=session_id)
        deleted_items = int(store_result.get("deleted_items", 0))

        audit = getattr(self.deps, "audit_log_store", None)
        if audit:
            try:
                audit.log_event(
                    action="paper_session_delete",
                    actor=ctx.payload.sub,
                    source="paper_download",
                    meta={
                        "session_id": session_id,
                        "delete_local_kb": bool(delete_local_kb),
                        "deleted_items": deleted_items,
                        "deleted_files": deleted_files,
                        "deleted_docs": deleted_docs,
                        "doc_error_count": len(doc_errors),
                    },
                    **actor_fields_from_ctx(self.deps, ctx),
                )
            except Exception:
                pass

        self._finish_job(session_id)
        return {
            "ok": True,
            "deleted_items": deleted_items,
            "deleted_files": deleted_files,
            "deleted_docs": deleted_docs,
            "doc_errors": doc_errors,
        }

    def content_disposition(self, filename: str) -> str:
        return self._content_disposition(filename)





