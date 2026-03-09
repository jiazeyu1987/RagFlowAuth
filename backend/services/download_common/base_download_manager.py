from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from backend.services.audit import AuditLogManager
from backend.services.download_execution import DownloadExecutionManager
from backend.services.download_history import DownloadHistoryManager
from backend.services.download_kb_lifecycle import DownloadKbLifecycleManager
from backend.services.download_pipeline import DownloadPipelineManager
from backend.services.llm_analysis import LLMAnalysisManager

from .manager_mixins import DownloadManagerDelegationMixin


class BaseDownloadManager(DownloadManagerDelegationMixin):
    def _initialize_common_manager(
        self,
        *,
        deps: Any,
        store_attr_name: str,
        store_factory: Callable[[], Any],
        item_to_dict: Callable[[Any], dict[str, Any]],
        session_to_dict: Callable[[Any], dict[str, Any]],
        namespace: str,
        llm_forced_id_env: str,
        llm_forced_name_env: str,
        llm_session_prefix: str,
        source_factory: Callable[[], Any],
    ) -> None:
        self.deps = deps
        self.store = getattr(deps, store_attr_name, None) or store_factory()
        self._item_to_dict = item_to_dict
        self._session_to_dict = session_to_dict
        self._audit_manager = getattr(deps, "audit_log_manager", None) or AuditLogManager(store=getattr(deps, "audit_log_store", None))
        self._execution_manager = DownloadExecutionManager(namespace=namespace)
        self._pipeline_manager = DownloadPipelineManager()
        self._history_manager = DownloadHistoryManager(owner=self)
        self._kb_lifecycle_manager = DownloadKbLifecycleManager(owner=self)
        self._llm_manager = LLMAnalysisManager(
            chat_service=getattr(deps, "ragflow_chat_service", None),
            forced_id_env=llm_forced_id_env,
            forced_name_env=llm_forced_name_env,
            session_prefix=llm_session_prefix,
        )
        self._source_factory = source_factory()
        self._source_registry = self._source_factory.create_registry()
        self._sources = self._source_registry.build_mapping()

    def _normalize_source_configs_common(
        self,
        *,
        source_configs: dict[str, Any] | None,
        source_keys: tuple[str, ...],
        default_limit: int,
        max_limit: int = 1000,
    ) -> dict[str, dict[str, Any]]:
        return self._execution_manager.normalize_source_configs(
            source_configs=source_configs,
            source_keys=source_keys,
            default_limit=default_limit,
            max_limit=max_limit,
        )

    def _build_source_stats_common(
        self,
        *,
        enabled_sources: list[str],
        source_cfg: dict[str, dict[str, Any]],
        default_limit: int,
    ) -> dict[str, dict[str, Any]]:
        return self._execution_manager.build_source_stats(
            enabled_sources=enabled_sources,
            source_cfg=source_cfg,
            default_limit=default_limit,
        )

    @staticmethod
    def _item_key_common(candidate: Any) -> str:
        return (
            str(getattr(candidate, "patent_id", "") or "").strip()
            or str(getattr(candidate, "publication_number", "") or "").strip()
            or str(getattr(candidate, "title", "") or "").strip()
        )

    @classmethod
    def _candidate_match_text_common(cls, candidate: Any) -> str:
        parts = [
            getattr(candidate, "title", None),
            getattr(candidate, "abstract_text", None),
            getattr(candidate, "assignee", None),
            getattr(candidate, "inventor", None),
            getattr(candidate, "publication_number", None),
            getattr(candidate, "patent_id", None),
        ]
        return " ".join(cls._normalize_match_text(x) for x in parts if str(x or "").strip())

    @classmethod
    def _candidate_matches_keywords_common(
        cls,
        *,
        candidate: Any,
        keywords: list[str],
        use_and: bool,
    ) -> bool:
        needles = [cls._normalize_match_text(k) for k in (keywords or []) if cls._normalize_match_text(k)]
        if not needles:
            return True
        haystack = cls._candidate_match_text_common(candidate)
        if not haystack:
            return False
        hits = [needle in haystack for needle in needles]
        return all(hits) if bool(use_and) else any(hits)

    def _build_item_row_common(
        self,
        *,
        source_key: str,
        source_index: int,
        candidate: Any,
        session_dir: Path,
    ) -> dict[str, Any]:
        safe_title = self._strip_html(getattr(candidate, "title", None))
        safe_abstract = self._strip_html(getattr(candidate, "abstract_text", None))
        preferred_name = str(getattr(candidate, "publication_number", None) or "").strip() or safe_title or f"{source_key}_{source_index}"
        filename = self._safe_filename(preferred_name, fallback=f"{source_key}_{source_index}")
        source_dir = session_dir / source_key
        source_dir.mkdir(parents=True, exist_ok=True)
        local_path = source_dir / filename

        status = "downloaded"
        error = None
        file_size: int | None = None
        mime_type = self._MIME_TYPE_DEFAULT

        pdf_url = str(getattr(candidate, "pdf_url", "") or "").strip()
        if not pdf_url:
            status = "failed"
            error = "missing_pdf_url"
        else:
            try:
                content = self._download_pdf_bytes(pdf_url)
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
            "source": getattr(candidate, "source", None),
            "source_label": getattr(candidate, "source_label", None),
            "patent_id": getattr(candidate, "patent_id", None),
            "title": safe_title,
            "abstract_text": safe_abstract,
            "publication_number": getattr(candidate, "publication_number", None),
            "publication_date": getattr(candidate, "publication_date", None),
            "inventor": getattr(candidate, "inventor", None),
            "assignee": getattr(candidate, "assignee", None),
            "detail_url": getattr(candidate, "detail_url", None),
            "pdf_url": getattr(candidate, "pdf_url", None),
            "file_path": str(local_path) if status == "downloaded" else None,
            "filename": filename,
            "file_size": file_size,
            "mime_type": mime_type if status == "downloaded" else None,
            "status": status,
            "error": error,
        }

    def _build_reused_row_common(
        self,
        *,
        source_key: str,
        source_index: int,
        candidate: Any,
        reused: Any,
    ) -> dict[str, Any]:
        return {
            "source": getattr(candidate, "source", None),
            "source_label": getattr(candidate, "source_label", None),
            "patent_id": getattr(candidate, "patent_id", None),
            "title": self._strip_html(getattr(candidate, "title", None)),
            "abstract_text": self._strip_html(getattr(candidate, "abstract_text", None)),
            "publication_number": getattr(candidate, "publication_number", None),
            "publication_date": getattr(candidate, "publication_date", None),
            "inventor": getattr(candidate, "inventor", None),
            "assignee": getattr(candidate, "assignee", None),
            "detail_url": getattr(candidate, "detail_url", None),
            "pdf_url": getattr(candidate, "pdf_url", None),
            "file_path": reused.file_path,
            "filename": reused.filename or self._safe_filename(
                str(getattr(candidate, "publication_number", None) or getattr(candidate, "title", None) or f"{source_key}_{source_index}"),
                fallback=f"{source_key}_{source_index}",
            ),
            "file_size": reused.file_size,
            "mime_type": reused.mime_type or self._MIME_TYPE_DEFAULT,
            "status": "downloaded_cached",
            "error": None,
            "analysis_text": reused.analysis_text,
            "analysis_file_path": reused.analysis_file_path,
        }
