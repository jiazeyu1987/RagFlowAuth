from __future__ import annotations

import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings
from backend.services.download_common import utils as download_common_utils
from backend.services.download_common.base_download_manager import BaseDownloadManager
from backend.services.paper_download.store import PaperDownloadStore, item_to_dict, session_to_dict

from .sources import PaperCandidate, PaperSourceError, PaperSourceFactory


LOCAL_PAPERS_KB_REF = "[本地论文]"


class PaperDownloadManager(BaseDownloadManager):
    _DM_KIND = "paper"
    _DM_SOURCE_NAME = "paper_download"
    _DM_DEFAULT_LOCAL_KB_REF = LOCAL_PAPERS_KB_REF
    _DM_ENTITY_SOURCE_KEY = "paper_source"
    _DM_ENTITY_ID_KEY = "paper_id"
    _DM_DEFAULT_FILENAME_PREFIX = "paper"
    _DM_ADD_REVIEW_NOTES = "added_from_paper_download"
    _DM_ANALYSIS_REVIEW_NOTES = "added_paper_analysis_from_paper_download"
    _SOURCE_ORDER = ("arxiv", "pubmed", "europe_pmc", "openalex")
    _MIME_TYPE_DEFAULT = "application/pdf"
    _DOWNLOAD_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )

    def __init__(self, deps: Any):
        self._initialize_common_manager(
            deps=deps,
            store_attr_name="paper_download_store",
            store_factory=PaperDownloadStore,
            item_to_dict=item_to_dict,
            session_to_dict=session_to_dict,
            namespace="paper_download",
            llm_forced_id_env="PAPER_ANALYSIS_CHAT_ID",
            llm_forced_name_env="PAPER_ANALYSIS_CHAT_NAME",
            llm_session_prefix="paper-auto-analyze",
            source_factory=PaperSourceFactory,
        )

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

    def _normalize_source_configs(self, source_configs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        return self._normalize_source_configs_common(
            source_configs=source_configs,
            source_keys=self._SOURCE_ORDER,
            default_limit=30,
            max_limit=1000,
        )

    @staticmethod
    def _safe_filename(name: str, fallback: str) -> str:
        return download_common_utils.safe_pdf_filename(name, fallback, default_base="paper")

    def _download_root(self) -> Path:
        return self._execution_manager.download_root(
            setting_value=settings.PAPER_DOWNLOAD_DIR,
            setting_name="PAPER_DOWNLOAD_DIR",
        )

    @staticmethod
    def _item_key(candidate: PaperCandidate) -> str:
        return BaseDownloadManager._item_key_common(candidate)

    @classmethod
    def _candidate_match_text(cls, candidate: PaperCandidate) -> str:
        return cls._candidate_match_text_common(candidate)

    @classmethod
    def _candidate_matches_keywords(cls, *, candidate: PaperCandidate, keywords: list[str], use_and: bool) -> bool:
        return cls._candidate_matches_keywords_common(candidate=candidate, keywords=keywords, use_and=use_and)

    def _build_source_stats(self, enabled: list[str], cfg: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return self._build_source_stats_common(
            enabled_sources=enabled,
            source_cfg=cfg,
            default_limit=30,
        )

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

    def _build_item_row(self, *, source_key: str, source_index: int, candidate: PaperCandidate, session_dir: Path) -> dict[str, Any]:
        return self._build_item_row_common(
            source_key=source_key,
            source_index=source_index,
            candidate=candidate,
            session_dir=session_dir,
        )

    def _candidate_matches_for_pipeline(
        self,
        source_key: str,
        candidate: PaperCandidate,
        keywords: list[str],
        use_and: bool,
    ) -> bool:
        return self._candidate_matches_keywords(candidate=candidate, keywords=keywords, use_and=use_and)

    def _build_reused_row(
        self,
        source_key: str,
        source_index: int,
        candidate: PaperCandidate,
        reused: Any,
    ) -> dict[str, Any]:
        return self._build_reused_row_common(
            source_key=source_key,
            source_index=source_index,
            candidate=candidate,
            reused=reused,
        )

    def _maybe_auto_analyze_item(self, actor: str, item: Any, auto_analyze: bool) -> tuple[bool, str | None, str | None]:
        if not bool(auto_analyze):
            return False, None, None
        should_analyze_pdf = self._is_downloaded_status(item.status)
        should_analyze_detail = (
            str(item.status or "") == "failed"
            and (
                str(item.error or "") == "missing_pdf_url"
                or str(item.error or "").startswith("download_failed:")
            )
        )
        if not (should_analyze_pdf or should_analyze_detail):
            return False, None, None
        if should_analyze_pdf:
            analysis_text, analysis_path = self._run_item_auto_analysis(actor=actor, item=item)
        else:
            analysis_text, analysis_path = self._run_item_detail_auto_analysis(actor=actor, item=item)
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
            candidate_type=PaperCandidate,
            source_error_type=PaperSourceError,
            session_dir=self._session_dir(actor_id=actor, session_id=session_id),
            source_default_limit=30,
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

        try:
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
                name_prefix="paper-download",
            )
        except Exception as e:
            self.store.update_session_runtime(
                session_id=session_id,
                status="failed",
                error=f"start_job_failed: {e}",
                source_errors=source_errors_seed,
                source_stats=source_stats,
            )
            raise HTTPException(status_code=500, detail="download_start_failed")

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
