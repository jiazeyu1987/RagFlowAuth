from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import html
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.kb_refs import resolve_kb_ref
from backend.app.core.paths import resolve_repo_path
from backend.app.core.permission_resolver import assert_can_delete, assert_can_upload, assert_kb_allowed
from backend.services.audit import AuditLogManager
from backend.services.download_execution import DownloadExecutionManager
from backend.services.download_history import DownloadHistoryManager
from backend.services.download_kb_lifecycle import DownloadKbLifecycleManager
from backend.services.download_pipeline import DownloadPipelineManager
from backend.services.documents.document_manager import DocumentManager
from backend.services.llm_analysis import LLMAnalysisManager
from backend.services.patent_download.store import PatentDownloadStore, item_to_dict, session_to_dict
from backend.services.unified_preview import build_preview_payload

from .sources import PatentCandidate, PatentSourceError, PatentSourceFactory


LOCAL_PATENTS_KB_REF = "[本地专利]"
LOCAL_PAPERS_KB_REF = LOCAL_PATENTS_KB_REF


class PatentDownloadManager:
    _SOURCE_ORDER = ("uspto", "google_patents")
    _MIME_TYPE_DEFAULT = "application/pdf"
    _DOWNLOAD_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )
    @staticmethod
    def _is_downloaded_status(status: str | None) -> bool:
        return str(status or "").strip().lower() in {"downloaded", "downloaded_cached"}

    @staticmethod
    def _is_true(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def __init__(self, deps: Any):
        self.deps = deps
        self.store: PatentDownloadStore = getattr(deps, "patent_download_store", None) or PatentDownloadStore()
        self._audit_manager = getattr(deps, "audit_log_manager", None) or AuditLogManager(store=getattr(deps, "audit_log_store", None))
        self._execution_manager = DownloadExecutionManager(namespace="patent_download")
        self._pipeline_manager = DownloadPipelineManager()
        self._history_manager = DownloadHistoryManager(owner=self)
        self._kb_lifecycle_manager = DownloadKbLifecycleManager(owner=self)
        self._llm_manager = LLMAnalysisManager(
            chat_service=getattr(deps, "ragflow_chat_service", None),
            forced_id_env="PATENT_ANALYSIS_CHAT_ID",
            forced_name_env="PATENT_ANALYSIS_CHAT_NAME",
            session_prefix="patent-auto-analyze",
        )
        self._source_factory = PatentSourceFactory()
        self._source_registry = self._source_factory.create_registry()
        self._sources = self._source_registry.build_mapping()

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
    def _contains_chinese(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))

    @staticmethod
    def _normalize_source_configs(source_configs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        return DownloadExecutionManager(namespace="patent_download").normalize_source_configs(
            source_configs=source_configs,
            source_keys=("uspto", "google_patents"),
            default_limit=10,
            max_limit=1000,
        )

    @staticmethod
    def _safe_filename(name: str, fallback: str) -> str:
        base = str(name or "").strip() or str(fallback or "patent").strip()
        base = re.sub(r"[\\/:*?\"<>|]+", "_", base).strip(" .")
        if not base:
            base = "patent"
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
        return self._execution_manager.download_root(
            setting_value=getattr(settings, "PATENT_DOWNLOAD_DIR", "data/patent_downloads"),
            fallback_dir="data/patent_downloads",
        )

    def _session_dir(self, *, actor_id: str, session_id: str) -> Path:
        return self._execution_manager.session_dir(
            root=self._download_root(),
            actor_id=actor_id,
            session_id=session_id,
        )

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
    def _item_key(candidate: PatentCandidate) -> str:
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
    def _candidate_match_text(cls, candidate: PatentCandidate) -> str:
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
    def _candidate_matches_keywords(cls, *, candidate: PatentCandidate, keywords: list[str], use_and: bool) -> bool:
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
        return DownloadExecutionManager(namespace="patent_download").build_source_stats(
            enabled_sources=enabled,
            source_cfg=cfg,
            default_limit=10,
        )

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
        return LLMAnalysisManager.extract_completion_answer(payload)

    @staticmethod
    def _is_chat_method_unsupported_error(text: str) -> bool:
        return LLMAnalysisManager.is_chat_method_unsupported_error(text)

    def _resolve_general_llm_chat_ids(self) -> list[str]:
        return self._llm_manager.resolve_general_llm_chat_ids()

    def _get_or_create_llm_session(
        self,
        *,
        actor: str,
        chat_id: str,
        force_new: bool = False,
        session_name: str | None = None,
    ) -> str:
        return self._llm_manager.get_or_create_session(
            actor=actor,
            chat_id=chat_id,
            force_new=force_new,
            session_name=session_name,
        )

    def _ask_general_llm(self, *, actor: str, question: str, per_item_session_tag: str | None = None) -> str:
        return self._llm_manager.ask(actor=actor, question=question, per_item_session_tag=per_item_session_tag)

    def _build_analysis_prompt(self, *, item: Any) -> str:
        return (
            "你是专利保护分析助手。请根据以下专利信息，提炼“应重点保护的技术内容”，"
            "输出中文，使用简洁条目，最多8条，每条1-2句，避免空泛表述。\n\n"
            f"标题: {item.title or ''}\n"
            f"公开号: {item.publication_number or ''}\n"
            f"公开日期: {item.publication_date or ''}\n"
            f"发明人: {item.inventor or ''}\n"
            f"申请人: {item.assignee or ''}\n"
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
        return root / f"patent_{item.item_id}.analysis.txt"

    def _fetch_google_patent_claims_text(self, detail_url: str) -> str:
        url = str(detail_url or "").strip()
        if not url:
            raise RuntimeError("claims_detail_url_missing")
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
            raise RuntimeError(f"claims_page_fetch_failed: {e}") from e

        section_match = re.search(r'itemprop="claims"[^>]*>(.*?)</section>', raw, flags=re.IGNORECASE | re.DOTALL)
        claims_html = section_match.group(1) if section_match else raw
        claim_lines = re.findall(r'class="claim-text"[^>]*>(.*?)</div>', claims_html, flags=re.IGNORECASE | re.DOTALL)
        if not claim_lines:
            raise RuntimeError("claims_not_found")
        out: list[str] = []
        for line in claim_lines:
            text = self._strip_html(line)
            if text:
                out.append(text)
            if len(" ".join(out)) >= 8000:
                break
        claims_text = "\n".join(out).strip()
        if not claims_text:
            raise RuntimeError("claims_empty")
        return claims_text

    def _build_claims_analysis_prompt(self, *, item: Any, claims_text: str) -> str:
        return (
            "你是专利保护分析助手。以下是专利权利要求（Claims），"
            "请提炼“应重点保护的技术内容”，输出中文，使用简洁条目，最多8条，每条1-2句。\n\n"
            f"标题: {item.title or ''}\n"
            f"公开号: {item.publication_number or ''}\n"
            f"详情链接: {item.detail_url or ''}\n\n"
            "Claims:\n"
            f"{claims_text}\n"
        )

    def _run_item_claims_auto_analysis(self, *, actor: str, item: Any) -> tuple[str | None, str | None]:
        claims_text = self._fetch_google_patent_claims_text(str(getattr(item, "detail_url", "") or ""))
        question = self._build_claims_analysis_prompt(item=item, claims_text=claims_text)
        analysis_text = self._ask_general_llm(
            actor=actor,
            question=question,
            per_item_session_tag=f"s{getattr(item, 'session_id', '')}-i{getattr(item, 'item_id', 0)}-claims",
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

    def _build_item_row(self, *, source_key: str, source_index: int, candidate: PatentCandidate, session_dir: Path) -> dict[str, Any]:
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

    def _register_job(self, session_id: str, job: Any) -> None:
        self._execution_manager.register_job(session_id=session_id, job=job)

    def _cancel_job(self, session_id: str) -> Any:
        return self._execution_manager.cancel_job(session_id=session_id)

    def _is_cancelled(self, session_id: str) -> bool:
        return self._execution_manager.is_cancelled(session_id=session_id)

    def _request_stop(self, session_id: str) -> Any:
        return self._execution_manager.request_stop(session_id=session_id)

    def _is_stop_requested(self, session_id: str) -> bool:
        return self._execution_manager.is_stop_requested(session_id=session_id)

    def _finish_job(self, session_id: str) -> None:
        self._execution_manager.finish_job(session_id=session_id)

    def _candidate_matches_for_pipeline(
        self,
        source_key: str,
        candidate: PatentCandidate,
        keywords: list[str],
        use_and: bool,
    ) -> bool:
        if source_key != "google_patents":
            return True
        return self._candidate_matches_keywords(candidate=candidate, keywords=keywords, use_and=use_and)

    def _build_reused_row(
        self,
        source_key: str,
        source_index: int,
        candidate: PatentCandidate,
        reused: Any,
    ) -> dict[str, Any]:
        return {
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

    def _maybe_auto_analyze_item(self, actor: str, item: Any, auto_analyze: bool) -> tuple[bool, str | None, str | None]:
        if not bool(auto_analyze):
            return False, None, None
        should_analyze_pdf = self._is_downloaded_status(item.status)
        should_analyze_claims = (
            str(item.status or "") == "failed"
            and str(item.error or "") == "missing_pdf_url"
            and str(item.source or "") == "google_patents"
        )
        if not (should_analyze_pdf or should_analyze_claims):
            return False, None, None
        if should_analyze_pdf:
            analysis_text, analysis_path = self._run_item_auto_analysis(actor=actor, item=item)
        else:
            analysis_text, analysis_path = self._run_item_claims_auto_analysis(actor=actor, item=item)
        return True, analysis_text, analysis_path

    @staticmethod
    def _analysis_failure_text(error: Exception) -> str:
        return f"auto_analyze_failed: {error}"

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
        self._pipeline_manager.run_job(
            owner=self,
            session_id=session_id,
            actor=actor,
            query=query,
            keywords=keywords,
            use_and=use_and,
            source_queries=source_queries,
            source_errors_seed=source_errors_seed,
            auto_analyze=auto_analyze,
            enabled_sources=enabled_sources,
            source_cfg=source_cfg,
            candidate_type=PatentCandidate,
            source_error_type=PatentSourceError,
            session_dir=self._session_dir(actor_id=actor, session_id=session_id),
            source_default_limit=10,
            candidate_matches=self._candidate_matches_for_pipeline,
            build_reused_row=self._build_reused_row,
            build_item_row=self._build_item_row,
            maybe_auto_analyze=self._maybe_auto_analyze_item,
            analysis_failure_text=self._analysis_failure_text,
        )

    def stop_session_download(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="patent_session_not_found")
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
            raise HTTPException(status_code=403, detail="patent_session_not_allowed")

    def _resolve_session_and_item(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[Any, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="patent_session_not_found")
        self._assert_session_access(session, ctx)
        item = self.store.get_item(session_id=session_id, item_id=item_id)
        if not item:
            raise HTTPException(status_code=404, detail="patent_item_not_found")
        return session, item

    def _ensure_file_bytes(self, *, file_path: str | None, filename: str | None) -> bytes:
        path = Path(str(file_path or ""))
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail=f"patent_file_not_found: {filename or ''}")
        try:
            return path.read_bytes()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"patent_file_read_failed: {e}") from e

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
        source_queries: dict[str, str] = {key: query for key in enabled_sources}
        source_errors_seed: dict[str, str] = {}
        if "uspto" in enabled_sources:
            try:
                if self._contains_chinese(query):
                    source_queries["uspto"] = self._translate_query_for_uspto(query)
                else:
                    source_queries["uspto"] = query
            except Exception as e:
                source_queries["uspto"] = query
                source_errors_seed["uspto"] = f"translate_failed_fallback_original_query: {e}"

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

        self._execution_manager.start_job(
            session_id=session_id,
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
            name_prefix="patent-download",
        )

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
            "downloaded": sum(1 for i in items if PatentDownloadManager._is_downloaded_status(i.status)),
            "failed": sum(1 for i in items if not PatentDownloadManager._is_downloaded_status(i.status)),
            "added": sum(1 for i in items if bool(i.added_doc_id)),
            "analyzed": sum(1 for i in items if bool(getattr(i, "analysis_text", None))),
        }

    def get_session_payload(self, *, session_id: str, ctx: Any) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="patent_session_not_found")
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
        return self._history_manager.list_history_keywords(ctx=ctx)

    def get_history_group_payload(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        return self._history_manager.get_history_group_payload(history_key=history_key, ctx=ctx)

    def delete_history_group(self, *, history_key: str, ctx: Any) -> dict[str, Any]:
        return self._history_manager.delete_history_group(history_key=history_key, ctx=ctx)

    def add_history_group_to_local_kb(self, *, history_key: str, ctx: Any, kb_ref: str = LOCAL_PATENTS_KB_REF) -> dict[str, Any]:
        return self._history_manager.add_history_group_to_local_kb(history_key=history_key, ctx=ctx, kb_ref=kb_ref)

    def get_item_preview_payload(self, *, session_id: str, item_id: int, ctx: Any, render: str = "default") -> dict[str, Any]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        return build_preview_payload(content, item.filename or f"patent_{item_id}.pdf", doc_id=str(item_id), render=render)

    def get_item_download_payload(self, *, session_id: str, item_id: int, ctx: Any) -> tuple[bytes, str, str]:
        _, item = self._resolve_session_and_item(session_id=session_id, item_id=item_id, ctx=ctx)
        content = self._ensure_file_bytes(file_path=item.file_path, filename=item.filename)
        filename = item.filename or f"patent_{item_id}.pdf"
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
        kb_ref: str = LOCAL_PATENTS_KB_REF,
        from_batch: bool = False,
    ) -> dict[str, Any]:
        try:
            return self._kb_lifecycle_manager.add_item_to_local_kb(
                session_id=session_id,
                item_id=item_id,
                ctx=ctx,
                kb_ref=kb_ref,
                from_batch=from_batch,
                action_name="patent_kb_add",
                source_name="patent_download",
                entity_source_key="patent_source",
                entity_id_key="patent_id",
                default_filename_prefix="patent",
                add_review_notes="added_from_patent_download",
                analysis_review_notes="added_patent_analysis_from_patent_download",
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                if not str(e.detail).startswith("patent_add_to_kb_failed:"):
                    raise HTTPException(status_code=e.status_code, detail=f"patent_add_to_kb_failed: {e.detail}") from e
                raise
            raise HTTPException(status_code=500, detail=f"patent_add_to_kb_failed: {e}") from e

    def add_all_to_local_kb(
        self,
        *,
        session_id: str,
        ctx: Any,
        kb_ref: str = LOCAL_PATENTS_KB_REF,
    ) -> dict[str, Any]:
        return self._kb_lifecycle_manager.add_all_to_local_kb(
            session_id=session_id,
            ctx=ctx,
            kb_ref=kb_ref,
            session_not_found_detail="patent_session_not_found",
            action_name="patent_kb_add_all",
            source_name="patent_download",
            item_add_fn=self.add_item_to_local_kb,
        )

    def delete_item(self, *, session_id: str, item_id: int, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        return self._kb_lifecycle_manager.delete_item(
            session_id=session_id,
            item_id=item_id,
            ctx=ctx,
            delete_local_kb=delete_local_kb,
            not_found_detail="patent_item_not_found",
            action_name="patent_item_delete",
            source_name="patent_download",
        )

    def delete_session(self, *, session_id: str, ctx: Any, delete_local_kb: bool = True) -> dict[str, Any]:
        return self._kb_lifecycle_manager.delete_session(
            session_id=session_id,
            ctx=ctx,
            delete_local_kb=delete_local_kb,
            session_not_found_detail="patent_session_not_found",
            action_name="patent_session_delete",
            source_name="patent_download",
        )

    def content_disposition(self, filename: str) -> str:
        return self._content_disposition(filename)

