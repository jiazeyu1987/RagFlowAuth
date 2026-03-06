from __future__ import annotations

import re
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.services.audit import AuditLogManager
from backend.services.download_execution import DownloadExecutionManager
from backend.services.download_history import DownloadHistoryManager
from backend.services.download_kb_lifecycle import DownloadKbLifecycleManager
from backend.services.download_pipeline import DownloadPipelineManager
from backend.services.download_common import DownloadManagerDelegationMixin, utils as download_common_utils
from backend.services.llm_analysis import LLMAnalysisManager
from backend.services.patent_download.store import PatentDownloadStore, item_to_dict, session_to_dict

from .sources import PatentCandidate, PatentSourceError, PatentSourceFactory


LOCAL_PATENTS_KB_REF = "[本地专利]"
LOCAL_PAPERS_KB_REF = LOCAL_PATENTS_KB_REF


class PatentDownloadManager(DownloadManagerDelegationMixin):
    _DM_KIND = "patent"
    _DM_SOURCE_NAME = "patent_download"
    _DM_DEFAULT_LOCAL_KB_REF = LOCAL_PATENTS_KB_REF
    _DM_ENTITY_SOURCE_KEY = "patent_source"
    _DM_ENTITY_ID_KEY = "patent_id"
    _DM_DEFAULT_FILENAME_PREFIX = "patent"
    _DM_ADD_REVIEW_NOTES = "added_from_patent_download"
    _DM_ANALYSIS_REVIEW_NOTES = "added_patent_analysis_from_patent_download"
    _SOURCE_ORDER = ("uspto", "google_patents")
    _MIME_TYPE_DEFAULT = "application/pdf"
    _DOWNLOAD_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )
    def __init__(self, deps: Any):
        self.deps = deps
        self.store: PatentDownloadStore = getattr(deps, "patent_download_store", None) or PatentDownloadStore()
        self._item_to_dict = item_to_dict
        self._session_to_dict = session_to_dict
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

    def _normalize_source_configs(self, source_configs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        return self._execution_manager.normalize_source_configs(
            source_configs=source_configs,
            source_keys=("uspto", "google_patents"),
            default_limit=10,
            max_limit=1000,
        )

    @staticmethod
    def _safe_filename(name: str, fallback: str) -> str:
        return download_common_utils.safe_pdf_filename(name, fallback, default_base="patent")

    def _download_root(self) -> Path:
        return self._execution_manager.download_root(
            setting_value=getattr(settings, "PATENT_DOWNLOAD_DIR", "data/patent_downloads"),
            fallback_dir="data/patent_downloads",
        )

    @staticmethod
    def _item_key(candidate: PatentCandidate) -> str:
        return (
            str(candidate.patent_id or "").strip()
            or str(candidate.publication_number or "").strip()
            or str(candidate.title or "").strip()
        )

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

    def _build_source_stats(self, enabled: list[str], cfg: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return self._execution_manager.build_source_stats(
            enabled_sources=enabled,
            source_cfg=cfg,
            default_limit=10,
        )

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

        session_data = self._session_to_dict(session)
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
