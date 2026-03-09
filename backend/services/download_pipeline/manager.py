from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Callable


class DownloadPipelineManager:
    def run_job(
        self,
        *,
        owner: Any,
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
        candidate_type: type,
        source_error_type: type[Exception],
        session_dir: Path,
        source_default_limit: int,
        candidate_matches: Callable[[str, Any, list[str], bool], bool],
        build_reused_row: Callable[[str, int, Any, Any], dict[str, Any]],
        build_item_row: Callable[[str, int, Any, Path], dict[str, Any]],
        maybe_auto_analyze: Callable[[str, Any, bool], tuple[bool, str | None, str | None]],
        analysis_failure_text: Callable[[Exception], str],
    ) -> None:
        source_errors: dict[str, str] = dict(source_errors_seed or {})
        source_stats = owner._build_source_stats(enabled_sources, source_cfg)
        queues: dict[str, deque[tuple[int, Any]]] = {}
        seen: set[str] = set()

        def _update_runtime(*, status: str, error: str | None = None) -> None:
            owner.store.update_session_runtime(
                session_id=session_id,
                status=status,
                error=error,
                source_errors=source_errors,
                source_stats=source_stats,
            )

        def _inc_failed_reason(source_key: str, reason: str) -> None:
            stats = source_stats.get(source_key, {})
            failed_reasons = stats.get("failed_reasons")
            if not isinstance(failed_reasons, dict):
                failed_reasons = {}
                stats["failed_reasons"] = failed_reasons
            key = str(reason or "unknown_failed_reason")
            failed_reasons[key] = int(failed_reasons.get(key, 0) or 0) + 1

        def _mark_stopped() -> None:
            for key in enabled_sources:
                queue = queues.get(key)
                if queue:
                    source_stats[key]["skipped_stopped"] = int(source_stats[key].get("skipped_stopped", 0) or 0) + len(queue)
            _update_runtime(status="stopped")

        for key in enabled_sources:
            source_stats[key]["query"] = str(source_queries.get(key) or query or "")

        try:
            for source_key in enabled_sources:
                if owner._is_cancelled(session_id):
                    _mark_stopped()
                    return
                if owner._is_stop_requested(session_id):
                    _mark_stopped()
                    return

                provider = owner._sources.get(source_key)
                if provider is None:
                    source_errors[source_key] = "source_not_implemented"
                    _update_runtime(status="running")
                    continue

                limit = int(source_cfg.get(source_key, {}).get("limit", source_default_limit) or source_default_limit)
                source_query = str(source_queries.get(source_key) or query or "").strip()
                source_stats[source_key]["query"] = source_query
                try:
                    raw = provider.search(query=source_query, limit=limit)
                except source_error_type as exc:
                    source_errors[source_key] = str(exc)
                    _update_runtime(status="running")
                    continue
                except Exception as exc:  # noqa: BLE001
                    source_errors[source_key] = f"source_failed: {exc}"
                    _update_runtime(status="running")
                    continue

                raw_candidates = [(idx + 1, item) for idx, item in enumerate(raw or []) if isinstance(item, candidate_type)]
                source_stats[source_key]["candidates"] = len(raw_candidates)

                typed: list[tuple[int, Any]] = []
                for idx, item in enumerate(raw or []):
                    if not isinstance(item, candidate_type):
                        continue
                    if not candidate_matches(source_key, item, keywords, use_and):
                        source_stats[source_key]["skipped_keyword"] = int(source_stats[source_key].get("skipped_keyword", 0) or 0) + 1
                        continue
                    typed.append((idx + 1, item))
                if not typed:
                    source_errors.setdefault(source_key, "no_results")
                queues[source_key] = deque(typed)
                _update_runtime(status="running")

            while True:
                if owner._is_cancelled(session_id):
                    _mark_stopped()
                    return
                if owner._is_stop_requested(session_id):
                    _mark_stopped()
                    return

                progressed = False
                for source_key in enabled_sources:
                    queue = queues.get(source_key)
                    if not queue:
                        continue
                    while queue:
                        if owner._is_cancelled(session_id):
                            _mark_stopped()
                            return
                        if owner._is_stop_requested(session_id):
                            _mark_stopped()
                            return

                        source_index, candidate = queue.popleft()
                        item_key = owner._item_key(candidate)
                        if item_key and item_key in seen:
                            source_stats[source_key]["skipped_duplicate"] = int(source_stats[source_key].get("skipped_duplicate", 0) or 0) + 1
                            continue
                        if item_key:
                            seen.add(item_key)

                        reused = owner.store.find_reusable_download(
                            created_by=actor,
                            patent_id=getattr(candidate, "patent_id", None),
                            publication_number=getattr(candidate, "publication_number", None),
                            title=owner._strip_html(getattr(candidate, "title", None)),
                        )
                        if reused and str(getattr(reused, "file_path", "") or "").strip() and Path(str(reused.file_path)).exists():
                            row = build_reused_row(source_key, source_index, candidate, reused)
                            source_stats[source_key]["reused"] += 1
                        else:
                            row = build_item_row(
                                source_key=source_key,
                                source_index=source_index,
                                candidate=candidate,
                                session_dir=session_dir,
                            )

                        if owner._is_downloaded_status(row.get("status")):
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

                        created_item = owner.store.create_item(session_id=session_id, item=row)
                        if bool(auto_analyze) and not str(getattr(created_item, "analysis_text", "") or "").strip():
                            attempted = False
                            try:
                                attempted, analysis_text, analysis_path = maybe_auto_analyze(actor, created_item, bool(auto_analyze))
                                if attempted:
                                    created_item = owner.store.update_item_analysis(
                                        session_id=session_id,
                                        item_id=created_item.item_id,
                                        analysis_text=analysis_text,
                                        analysis_file_path=analysis_path,
                                    ) or created_item
                            except Exception as analysis_error:  # noqa: BLE001
                                if attempted or bool(auto_analyze):
                                    source_errors[source_key] = f"auto_analyze_failed: {analysis_error}"
                                    owner.store.update_item_analysis(
                                        session_id=session_id,
                                        item_id=created_item.item_id,
                                        analysis_text=analysis_failure_text(analysis_error),
                                        analysis_file_path=None,
                                    )

                        _update_runtime(status="running")
                        progressed = True
                        break

                if not progressed:
                    break

            _update_runtime(status="completed")
        except Exception as exc:  # noqa: BLE001
            _update_runtime(status="failed", error=f"download_job_failed: {exc}")
        finally:
            owner._finish_job(session_id)
