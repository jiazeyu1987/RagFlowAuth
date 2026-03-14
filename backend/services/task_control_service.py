from __future__ import annotations

import asyncio
import copy
import logging
import time
from collections import defaultdict
from typing import Any

from backend.app.core.authz import AuthContext
from backend.app.core.config import settings
from backend.services.nas_browser_service import NasBrowserService
from backend.services.paper_plag_store import PaperPlagStore
from backend.services.paper_download.manager import PaperDownloadManager
from backend.services.paper_download.store import session_to_dict as paper_session_to_dict
from backend.services.patent_download.manager import PatentDownloadManager
from backend.services.patent_download.store import session_to_dict as patent_session_to_dict

logger = logging.getLogger(__name__)

_METRIC_ALERT_CACHE: dict[str, float] = {}
_METRIC_SNAPSHOT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_TASK_KIND_CACHE: dict[str, tuple[float, str]] = {}
_TASK_PAYLOAD_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_METRIC_FETCH_LOCKS: dict[str, asyncio.Lock] = {}
_TASK_PAYLOAD_FETCH_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}
_BACKUP_TERMINAL_STATUSES = {"completed", "failed", "canceled"}


class TaskControlService:
    AUTO_KIND = "auto"
    ALL_KIND = "all"
    COLLECTION_KIND = "collection"
    NAS_IMPORT_KIND = "nas_import"
    BACKUP_JOB_KIND = "backup_job"
    PAPER_DOWNLOAD_KIND = "paper_download"
    PATENT_DOWNLOAD_KIND = "patent_download"
    PAPER_PLAG_KIND = "paper_plagiarism"
    KNOWLEDGE_UPLOAD_KIND = "knowledge_upload"

    @staticmethod
    def _task_kind_cache_ttl_seconds() -> float:
        try:
            ttl = float(getattr(settings, "TASK_KIND_CACHE_TTL_SECONDS", 300) or 0.0)
        except Exception:
            ttl = 300.0
        return max(0.0, min(ttl, 3600.0))

    @classmethod
    def _read_cached_task_kind(cls, task_id: str) -> str | None:
        cache_ttl_s = cls._task_kind_cache_ttl_seconds()
        if cache_ttl_s <= 0:
            return None
        now_ts = time.monotonic()
        key = str(task_id or "").strip()
        if not key:
            return None
        cached = _TASK_KIND_CACHE.get(key)
        if not cached:
            return None
        cached_at, cached_kind = cached
        if (now_ts - cached_at) > cache_ttl_s:
            _TASK_KIND_CACHE.pop(key, None)
            return None
        return str(cached_kind or "").strip().lower() or None

    @classmethod
    def _remember_task_kind(cls, task_id: str, *, task_kind: str) -> None:
        cache_ttl_s = cls._task_kind_cache_ttl_seconds()
        if cache_ttl_s <= 0:
            return
        key = str(task_id or "").strip()
        normalized_kind = str(task_kind or "").strip().lower()
        if not key or normalized_kind not in (
            cls.NAS_IMPORT_KIND,
            cls.BACKUP_JOB_KIND,
            cls.PAPER_DOWNLOAD_KIND,
            cls.PATENT_DOWNLOAD_KIND,
            cls.PAPER_PLAG_KIND,
            cls.KNOWLEDGE_UPLOAD_KIND,
        ):
            return
        if len(_TASK_KIND_CACHE) > 5000:
            _TASK_KIND_CACHE.clear()
        _TASK_KIND_CACHE[key] = (time.monotonic(), normalized_kind)

    @staticmethod
    def _task_payload_cache_ttl_seconds() -> float:
        try:
            ttl_ms = int(getattr(settings, "TASK_STATUS_CACHE_TTL_MS", 1500) or 0)
        except Exception:
            ttl_ms = 1500
        ttl_ms = max(0, min(ttl_ms, 5000))
        return float(ttl_ms) / 1000.0

    @staticmethod
    def _task_payload_cache_key(*, task_id: str, task_kind: str) -> tuple[str, str]:
        return (str(task_kind or "").strip().lower(), str(task_id or "").strip())

    @classmethod
    def _read_cached_task_payload(cls, *, task_id: str, task_kind: str) -> dict[str, Any] | None:
        ttl_s = cls._task_payload_cache_ttl_seconds()
        if ttl_s <= 0:
            return None
        key = cls._task_payload_cache_key(task_id=task_id, task_kind=task_kind)
        cached = _TASK_PAYLOAD_CACHE.get(key)
        if not cached:
            return None
        cached_at, payload = cached
        if (time.monotonic() - cached_at) > ttl_s:
            _TASK_PAYLOAD_CACHE.pop(key, None)
            return None
        return copy.deepcopy(payload)

    @classmethod
    def _remember_task_payload(cls, *, task_id: str, task_kind: str, payload: dict[str, Any]) -> None:
        ttl_s = cls._task_payload_cache_ttl_seconds()
        if ttl_s <= 0:
            return
        key = cls._task_payload_cache_key(task_id=task_id, task_kind=task_kind)
        if len(_TASK_PAYLOAD_CACHE) > 8000:
            _TASK_PAYLOAD_CACHE.clear()
        _TASK_PAYLOAD_CACHE[key] = (time.monotonic(), copy.deepcopy(payload))

    @classmethod
    def _invalidate_task_payload_cache(cls, task_id: str) -> None:
        key_task_id = str(task_id or "").strip()
        if not key_task_id:
            return
        for key in list(_TASK_PAYLOAD_CACHE.keys()):
            if key[1] == key_task_id:
                _TASK_PAYLOAD_CACHE.pop(key, None)

    @staticmethod
    def _is_not_found_error(exc: RuntimeError) -> bool:
        detail = str(exc or "")
        lowered = detail.lower()
        return ("not found" in lowered) or ("not_found" in lowered) or ("不存在" in detail)

    @staticmethod
    def _is_positive_int_task_id(task_id: str) -> bool:
        try:
            return int(str(task_id or "").strip()) > 0
        except Exception:
            return False

    @staticmethod
    async def _nas_task_exists(task_id: str, deps) -> bool:
        store = getattr(deps, "nas_task_store", None)
        if store is None:
            return False
        task = await asyncio.to_thread(store.get_task, task_id)
        return task is not None

    @staticmethod
    async def _backup_task_exists(task_id: str, deps) -> bool:
        store = getattr(deps, "data_security_store", None)
        if store is None:
            return False
        try:
            job_id = int(str(task_id or "").strip())
        except Exception:
            return False
        if job_id <= 0:
            return False
        try:
            await asyncio.to_thread(store.get_job, job_id)
        except Exception:
            return False
        return True

    @staticmethod
    async def _paper_task_exists(task_id: str, deps) -> bool:
        store = getattr(deps, "paper_download_store", None)
        if store is None:
            return False
        session = await asyncio.to_thread(store.get_session, str(task_id or "").strip())
        return session is not None

    @staticmethod
    async def _patent_task_exists(task_id: str, deps) -> bool:
        store = getattr(deps, "patent_download_store", None)
        if store is None:
            return False
        session = await asyncio.to_thread(store.get_session, str(task_id or "").strip())
        return session is not None

    @staticmethod
    def _paper_plag_store(deps):
        store = getattr(deps, "paper_plag_store", None)
        if store is not None:
            return store
        kb_store = getattr(deps, "kb_store", None)
        db_path = str(getattr(kb_store, "db_path", "") or "").strip()
        if not db_path:
            return None
        try:
            return PaperPlagStore(db_path=db_path)
        except Exception:
            return None

    @classmethod
    async def _paper_plag_task_exists(cls, task_id: str, deps) -> bool:
        store = cls._paper_plag_store(deps)
        if store is None:
            return False
        report = await asyncio.to_thread(store.get_report, str(task_id or "").strip())
        return report is not None

    @staticmethod
    async def _upload_task_exists(task_id: str, deps) -> bool:
        store = getattr(deps, "kb_store", None)
        if store is None:
            return False
        doc = await asyncio.to_thread(store.get_document, str(task_id or "").strip())
        return doc is not None

    async def _task_exists_by_kind(self, task_id: str, *, deps, task_kind: str) -> bool:
        if task_kind == self.NAS_IMPORT_KIND:
            return await self._nas_task_exists(task_id, deps)
        if task_kind == self.BACKUP_JOB_KIND:
            return await self._backup_task_exists(task_id, deps)
        if task_kind == self.PAPER_DOWNLOAD_KIND:
            return await self._paper_task_exists(task_id, deps)
        if task_kind == self.PATENT_DOWNLOAD_KIND:
            return await self._patent_task_exists(task_id, deps)
        if task_kind == self.PAPER_PLAG_KIND:
            return await self._paper_plag_task_exists(task_id, deps)
        if task_kind == self.KNOWLEDGE_UPLOAD_KIND:
            return await self._upload_task_exists(task_id, deps)
        return False

    @classmethod
    def _candidate_kinds_for_task_id(cls, task_id: str) -> tuple[str, ...]:
        if cls._is_positive_int_task_id(task_id):
            return (
                cls.BACKUP_JOB_KIND,
                cls.NAS_IMPORT_KIND,
                cls.PAPER_DOWNLOAD_KIND,
                cls.PATENT_DOWNLOAD_KIND,
                cls.PAPER_PLAG_KIND,
                cls.KNOWLEDGE_UPLOAD_KIND,
            )
        return (
            cls.NAS_IMPORT_KIND,
            cls.KNOWLEDGE_UPLOAD_KIND,
            cls.PAPER_PLAG_KIND,
            cls.PAPER_DOWNLOAD_KIND,
            cls.PATENT_DOWNLOAD_KIND,
            cls.BACKUP_JOB_KIND,
        )

    async def _resolve_collection_task_kind(self, task_id: str, *, deps) -> str:
        normalized_task_id = str(task_id or "").strip()
        cached_kind = self._read_cached_task_kind(normalized_task_id)
        if cached_kind in (self.PAPER_DOWNLOAD_KIND, self.PATENT_DOWNLOAD_KIND):
            if await self._task_exists_by_kind(normalized_task_id, deps=deps, task_kind=cached_kind):
                return cached_kind
            _TASK_KIND_CACHE.pop(normalized_task_id, None)

        for candidate_kind in (self.PAPER_DOWNLOAD_KIND, self.PATENT_DOWNLOAD_KIND):
            if await self._task_exists_by_kind(normalized_task_id, deps=deps, task_kind=candidate_kind):
                self._remember_task_kind(normalized_task_id, task_kind=candidate_kind)
                return candidate_kind
        raise RuntimeError("task not found")

    async def _resolve_kind(self, task_id: str, *, deps, task_kind: str | None = None) -> str:
        normalized_kind = str(task_kind or self.AUTO_KIND).strip().lower()
        if normalized_kind in (self.AUTO_KIND, self.ALL_KIND):
            if await self._nas_task_exists(task_id, deps):
                return self.NAS_IMPORT_KIND
            if await self._backup_task_exists(task_id, deps):
                return self.BACKUP_JOB_KIND
            raise RuntimeError("task not found")
        if normalized_kind == self.NAS_IMPORT_KIND:
            if await self._nas_task_exists(task_id, deps):
                return self.NAS_IMPORT_KIND
            raise RuntimeError("task not found")
        if normalized_kind == self.BACKUP_JOB_KIND:
            if await self._backup_task_exists(task_id, deps):
                return self.BACKUP_JOB_KIND
            raise RuntimeError("task not found")
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {normalized_kind}")

    def _resolve_metrics_kind(self, task_kind: str | None = None) -> str:
        normalized_kind = str(task_kind or self.ALL_KIND).strip().lower()
        if normalized_kind in (self.AUTO_KIND, self.ALL_KIND):
            return self.ALL_KIND
        if normalized_kind in (self.NAS_IMPORT_KIND, self.BACKUP_JOB_KIND):
            return normalized_kind
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {normalized_kind}")

    @staticmethod
    def _with_kind(payload: dict[str, Any], *, task_kind: str) -> dict[str, Any]:
        next_payload = dict(payload)
        next_payload["task_kind"] = task_kind
        return next_payload

    async def _get_nas_task_payload(self, task_id: str, *, deps, ctx: AuthContext) -> dict[str, Any]:
        store = getattr(deps, "nas_task_store", None)
        if store is None:
            raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")
        service = NasBrowserService(task_store=store)
        payload = await service.get_folder_import_task(task_id, deps=deps, ctx=ctx)
        self._remember_task_kind(task_id, task_kind=self.NAS_IMPORT_KIND)
        return self._with_kind(payload, task_kind=self.NAS_IMPORT_KIND)

    async def _get_backup_task_payload(self, task_id: str, *, deps) -> dict[str, Any]:
        store = getattr(deps, "data_security_store", None)
        if store is None:
            raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")
        job_id = self._parse_backup_job_id(task_id)
        try:
            job = await asyncio.to_thread(store.get_job, job_id)
        except Exception as exc:
            raise RuntimeError("task not found") from exc
        self._remember_task_kind(task_id, task_kind=self.BACKUP_JOB_KIND)
        return self._with_kind(self._backup_task_payload(job), task_kind=self.BACKUP_JOB_KIND)

    async def _resolve_kind(self, task_id: str, *, deps, task_kind: str | None = None) -> str:
        normalized_kind = str(task_kind or self.AUTO_KIND).strip().lower()
        if normalized_kind == self.COLLECTION_KIND:
            return await self._resolve_collection_task_kind(task_id, deps=deps)
        if normalized_kind in (
            self.NAS_IMPORT_KIND,
            self.BACKUP_JOB_KIND,
            self.COLLECTION_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        ):
            if await self._task_exists_by_kind(task_id, deps=deps, task_kind=normalized_kind):
                return normalized_kind
            raise RuntimeError("task not found")

        if normalized_kind not in (self.AUTO_KIND, self.ALL_KIND):
            raise RuntimeError(f"unsupported task kind: {normalized_kind}")

        cached_kind = self._read_cached_task_kind(task_id)
        if cached_kind in (
            self.NAS_IMPORT_KIND,
            self.BACKUP_JOB_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        ):
            if await self._task_exists_by_kind(task_id, deps=deps, task_kind=cached_kind):
                return cached_kind
            _TASK_KIND_CACHE.pop(str(task_id or "").strip(), None)

        for candidate_kind in self._candidate_kinds_for_task_id(task_id):
            if await self._task_exists_by_kind(task_id, deps=deps, task_kind=candidate_kind):
                self._remember_task_kind(task_id, task_kind=candidate_kind)
                return candidate_kind
        raise RuntimeError("task not found")

    def _resolve_metrics_kind(self, task_kind: str | None = None) -> str:
        normalized_kind = str(task_kind or self.ALL_KIND).strip().lower()
        if normalized_kind in (self.AUTO_KIND, self.ALL_KIND):
            return self.ALL_KIND
        if normalized_kind in (
            self.NAS_IMPORT_KIND,
            self.BACKUP_JOB_KIND,
            self.COLLECTION_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        ):
            return normalized_kind
        raise RuntimeError(f"unsupported task kind: {normalized_kind}")

    @staticmethod
    def _metric_thresholds() -> dict[str, Any]:
        return {
            "failure_rate": float(getattr(settings, "TASK_ALERT_FAILURE_RATE_THRESHOLD", 0.3) or 0.0),
            "backlog_tasks": int(getattr(settings, "TASK_ALERT_BACKLOG_THRESHOLD", 20) or 0),
            "avg_duration_ms": int(getattr(settings, "TASK_ALERT_AVG_DURATION_MS_THRESHOLD", 900000) or 0),
        }

    @staticmethod
    def _alert_log_cooldown_seconds() -> float:
        try:
            cooldown = float(getattr(settings, "TASK_ALERT_LOG_COOLDOWN_SECONDS", 120) or 0.0)
        except Exception:
            cooldown = 120.0
        return max(0.0, cooldown)

    @staticmethod
    def _metrics_cache_ttl_seconds() -> float:
        try:
            ttl_ms = int(getattr(settings, "TASK_METRICS_CACHE_TTL_MS", 800) or 0)
        except Exception:
            ttl_ms = 800
        ttl_ms = max(0, min(ttl_ms, 60_000))
        return float(ttl_ms) / 1000.0

    @staticmethod
    def _build_metric_alerts(*, task_kind: str, metrics: dict[str, Any], thresholds: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        failure_rate = float(metrics.get("failure_rate") or 0.0)
        backlog_tasks = int(metrics.get("backlog_tasks") or 0)
        avg_duration_ms = int(metrics.get("avg_duration_ms") or 0)

        failure_rate_threshold = float(thresholds.get("failure_rate") or 0.0)
        backlog_threshold = int(thresholds.get("backlog_tasks") or 0)
        avg_duration_threshold = int(thresholds.get("avg_duration_ms") or 0)

        if failure_rate_threshold > 0 and failure_rate >= failure_rate_threshold:
            alerts.append(
                {
                    "alert_id": f"{task_kind}:failure_rate",
                    "level": "warning",
                    "metric": "failure_rate",
                    "current_value": round(failure_rate, 4),
                    "threshold": failure_rate_threshold,
                    "message": "task_failure_rate_exceeded",
                }
            )

        if backlog_threshold > 0 and backlog_tasks >= backlog_threshold:
            alerts.append(
                {
                    "alert_id": f"{task_kind}:backlog_tasks",
                    "level": "warning",
                    "metric": "backlog_tasks",
                    "current_value": backlog_tasks,
                    "threshold": backlog_threshold,
                    "message": "task_backlog_exceeded",
                }
            )

        if avg_duration_threshold > 0 and avg_duration_ms >= avg_duration_threshold:
            alerts.append(
                {
                    "alert_id": f"{task_kind}:avg_duration_ms",
                    "level": "warning",
                    "metric": "avg_duration_ms",
                    "current_value": avg_duration_ms,
                    "threshold": avg_duration_threshold,
                    "message": "task_avg_duration_exceeded",
                }
            )

        return alerts

    @staticmethod
    def _emit_alert_logs(alerts: list[dict[str, Any]]) -> None:
        now_ts = time.monotonic()
        cooldown_s = TaskControlService._alert_log_cooldown_seconds()
        active_ids = {str(item.get("alert_id") or "") for item in alerts if item.get("alert_id")}

        # Keep cache bounded: prune inactive ids that have not logged for a while.
        stale_after_s = max(cooldown_s * 3.0, 300.0)
        for alert_id, logged_at in list(_METRIC_ALERT_CACHE.items()):
            if alert_id in active_ids:
                continue
            if (now_ts - logged_at) >= stale_after_s:
                _METRIC_ALERT_CACHE.pop(alert_id, None)

        for alert in alerts:
            alert_id = str(alert.get("alert_id") or "")
            if not alert_id:
                continue
            last_logged_at = _METRIC_ALERT_CACHE.get(alert_id)
            if last_logged_at is not None and (now_ts - last_logged_at) < cooldown_s:
                continue
            _METRIC_ALERT_CACHE[alert_id] = now_ts
            logger.warning("task_metric_alert %s", alert)

    @staticmethod
    def _parse_backup_job_id(task_id: str) -> int:
        try:
            job_id = int(str(task_id or "").strip())
        except Exception as exc:
            raise RuntimeError("task not found") from exc
        if job_id <= 0:
            raise RuntimeError("task not found")
        return job_id

    @staticmethod
    def _backup_status_to_unified(status: str) -> str:
        mapping = {
            "queued": "pending",
            "running": "running",
            "canceling": "canceling",
            "canceled": "canceled",
            "completed": "completed",
            "failed": "failed",
        }
        normalized = str(status or "").strip().lower()
        return mapping.get(normalized, normalized or "pending")

    @classmethod
    def _backup_task_payload(cls, job) -> dict[str, Any]:
        unified_status = cls._backup_status_to_unified(getattr(job, "status", ""))
        progress = int(max(0, min(100, getattr(job, "progress", 0) or 0)))
        can_cancel = unified_status in ("pending", "running", "canceling")
        can_retry = unified_status in _BACKUP_TERMINAL_STATUSES
        return {
            "task_id": str(job.id),
            "owner_user_id": "__system__",
            "task_priority": 100,
            "status": unified_status,
            "raw_status": str(getattr(job, "status", "") or ""),
            "progress_percent": progress,
            "remaining_percent": max(100 - progress, 0),
            "queue_position": None,
            "is_queued": unified_status == "pending",
            "max_concurrency": 1,
            "can_cancel": can_cancel,
            "can_pause": False,
            "can_resume": False,
            "can_retry": can_retry,
            "retry_count": 0,
            "quota": {
                "global_limit": 1,
                "task_kind_limit": 1,
                "per_user_limit": 1,
            },
            "quota_blocked_reason": None,
            "kind": str(getattr(job, "kind", "incremental") or "incremental"),
            "message": getattr(job, "message", None),
            "detail": getattr(job, "detail", None),
            "output_dir": getattr(job, "output_dir", None),
            "created_at_ms": int(getattr(job, "created_at_ms", 0) or 0),
            "started_at_ms": getattr(job, "started_at_ms", None),
            "finished_at_ms": getattr(job, "finished_at_ms", None),
            "cancel_requested_at_ms": getattr(job, "cancel_requested_at_ms", None),
            "cancel_reason": getattr(job, "cancel_reason", None),
            "canceled_at_ms": getattr(job, "canceled_at_ms", None),
        }

    async def get_task(self, task_id: str, *, deps, ctx: AuthContext, task_kind: str | None = None) -> dict[str, Any]:
        normalized_kind = str(task_kind or self.AUTO_KIND).strip().lower()
        if normalized_kind == self.NAS_IMPORT_KIND:
            return await self._get_nas_task_payload(task_id, deps=deps, ctx=ctx)
        if normalized_kind == self.BACKUP_JOB_KIND:
            return await self._get_backup_task_payload(task_id, deps=deps)
        if normalized_kind not in (self.AUTO_KIND, self.ALL_KIND):
            raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {normalized_kind}")

        cached_kind = self._read_cached_task_kind(task_id)
        if cached_kind == self.NAS_IMPORT_KIND:
            try:
                return await self._get_nas_task_payload(task_id, deps=deps, ctx=ctx)
            except RuntimeError as exc:
                if not self._is_not_found_error(exc):
                    raise
                _TASK_KIND_CACHE.pop(str(task_id or "").strip(), None)
        if cached_kind == self.BACKUP_JOB_KIND:
            try:
                return await self._get_backup_task_payload(task_id, deps=deps)
            except RuntimeError as exc:
                if not self._is_not_found_error(exc):
                    raise
                _TASK_KIND_CACHE.pop(str(task_id or "").strip(), None)

        # Heuristic: backup job ids are positive integers; this avoids an extra NAS lookup on common backup paths.
        is_positive_int_id = False
        try:
            is_positive_int_id = int(str(task_id or "").strip()) > 0
        except Exception:
            is_positive_int_id = False

        candidate_order = (
            (self.BACKUP_JOB_KIND, self.NAS_IMPORT_KIND) if is_positive_int_id else (self.NAS_IMPORT_KIND, self.BACKUP_JOB_KIND)
        )
        for candidate_kind in candidate_order:
            try:
                if candidate_kind == self.NAS_IMPORT_KIND:
                    return await self._get_nas_task_payload(task_id, deps=deps, ctx=ctx)
                return await self._get_backup_task_payload(task_id, deps=deps)
            except RuntimeError as exc:
                if not self._is_not_found_error(exc):
                    raise
                continue
        raise RuntimeError("task not found")

    async def pause_task(self, task_id: str, *, deps, task_kind: str | None = None) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        if resolved_kind == self.NAS_IMPORT_KIND:
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.pause_folder_import_task(task_id, deps=deps)
            return self._with_kind(payload, task_kind=resolved_kind)
        if resolved_kind == self.BACKUP_JOB_KIND:
            raise RuntimeError("褰撳墠浠诲姟绫诲瀷鏆備笉鏀寔鏆傚仠")
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {resolved_kind}")

    async def resume_task(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext,
        task_kind: str | None = None,
    ) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        if resolved_kind == self.NAS_IMPORT_KIND:
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.resume_folder_import_task(task_id, deps=deps, ctx=ctx)
            return self._with_kind(payload, task_kind=resolved_kind)
        if resolved_kind == self.BACKUP_JOB_KIND:
            raise RuntimeError("褰撳墠浠诲姟绫诲瀷鏆備笉鏀寔缁х画")
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {resolved_kind}")

    async def cancel_task(self, task_id: str, *, deps, task_kind: str | None = None) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        if resolved_kind == self.NAS_IMPORT_KIND:
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.cancel_folder_import_task(task_id, deps=deps)
            return self._with_kind(payload, task_kind=resolved_kind)
        if resolved_kind == self.BACKUP_JOB_KIND:
            store = getattr(deps, "data_security_store", None)
            if store is None:
                raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")
            job_id = self._parse_backup_job_id(task_id)
            try:
                job = await asyncio.to_thread(store.request_cancel_job, job_id)
            except Exception as exc:
                raise RuntimeError("task not found") from exc
            return self._with_kind(self._backup_task_payload(job), task_kind=resolved_kind)
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {resolved_kind}")

    async def retry_task(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext,
        task_kind: str | None = None,
    ) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        if resolved_kind == self.NAS_IMPORT_KIND:
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.retry_folder_import_task(task_id, deps=deps, ctx=ctx)
            return self._with_kind(payload, task_kind=resolved_kind)
        if resolved_kind == self.BACKUP_JOB_KIND:
            raise RuntimeError("褰撳墠浠诲姟绫诲瀷鏆備笉鏀寔閲嶈瘯")
        raise RuntimeError(f"鏆備笉鏀寔鐨勪换鍔＄被鍨? {resolved_kind}")

    async def _metrics_for_nas(self, *, deps) -> dict[str, Any]:
        store = getattr(deps, "nas_task_store", None)
        if store is None:
            raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")
        summary = await asyncio.to_thread(store.summary_metrics)
        total_tasks = int(summary.get("total_tasks") or 0)
        failed_tasks = int(summary.get("failed_tasks") or 0)
        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)
        return {
            "task_kind": self.NAS_IMPORT_KIND,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": int(summary.get("backlog_tasks") or 0),
            "avg_duration_ms": int(summary.get("avg_duration_ms") or 0),
            "failure_rate": failure_rate,
            "status_counts": summary.get("status_counts") or {},
        }

    async def _metrics_for_backup(self, *, deps, limit: int = 500) -> dict[str, Any]:
        store = getattr(deps, "data_security_store", None)
        if store is None:
            raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")
        jobs = await asyncio.to_thread(store.list_jobs, limit=max(1, min(2000, int(limit))))
        total_tasks = len(jobs)
        failed_tasks = 0
        backlog_tasks = 0
        durations: list[int] = []
        status_counts: dict[str, int] = defaultdict(int)

        for job in jobs:
            status = self._backup_status_to_unified(getattr(job, "status", ""))
            status_counts[status] += 1
            if status == "failed":
                failed_tasks += 1
            if status in ("pending", "running", "canceling"):
                backlog_tasks += 1
            if status in _BACKUP_TERMINAL_STATUSES:
                created_at = int(getattr(job, "created_at_ms", 0) or 0)
                finished_at = int(getattr(job, "finished_at_ms", 0) or 0)
                if created_at > 0 and finished_at >= created_at:
                    durations.append(finished_at - created_at)

        avg_duration_ms = int(sum(durations) / len(durations)) if durations else 0
        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)

        return {
            "task_kind": self.BACKUP_JOB_KIND,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": backlog_tasks,
            "avg_duration_ms": avg_duration_ms,
            "failure_rate": failure_rate,
            "status_counts": dict(status_counts),
        }

    @staticmethod
    def _merge_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
        if not metrics:
            return {
                "task_kind": "all",
                "total_tasks": 0,
                "failed_tasks": 0,
                "backlog_tasks": 0,
                "avg_duration_ms": 0,
                "failure_rate": 0.0,
                "status_counts": {},
                "metrics_by_kind": {},
            }

        total_tasks = sum(int(item.get("total_tasks") or 0) for item in metrics)
        failed_tasks = sum(int(item.get("failed_tasks") or 0) for item in metrics)
        backlog_tasks = sum(int(item.get("backlog_tasks") or 0) for item in metrics)
        weighted_duration = sum(
            int(item.get("avg_duration_ms") or 0) * int(item.get("total_tasks") or 0) for item in metrics
        )
        avg_duration_ms = int(weighted_duration / total_tasks) if total_tasks > 0 else 0
        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)

        status_counts: dict[str, int] = defaultdict(int)
        for item in metrics:
            for status, count in (item.get("status_counts") or {}).items():
                status_counts[str(status)] += int(count or 0)

        return {
            "task_kind": "all",
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": backlog_tasks,
            "avg_duration_ms": avg_duration_ms,
            "failure_rate": failure_rate,
            "status_counts": dict(status_counts),
            "metrics_by_kind": {str(item.get("task_kind")): item for item in metrics},
        }

    async def get_metrics(self, *, deps, task_kind: str | None = None) -> dict[str, Any]:
        resolved_kind = self._resolve_metrics_kind(task_kind)
        cache_ttl_s = self._metrics_cache_ttl_seconds()
        now_ts = time.monotonic()

        payload: dict[str, Any] | None = None
        if cache_ttl_s > 0:
            cached = _METRIC_SNAPSHOT_CACHE.get(resolved_kind)
            if cached and (now_ts - cached[0]) <= cache_ttl_s:
                payload = copy.deepcopy(cached[1])

        if payload is None:
            metrics_list: list[dict[str, Any]] = []
            if resolved_kind in (self.ALL_KIND, self.NAS_IMPORT_KIND):
                try:
                    metrics_list.append(await self._metrics_for_nas(deps=deps))
                except RuntimeError:
                    if resolved_kind == self.NAS_IMPORT_KIND:
                        raise
            if resolved_kind in (self.ALL_KIND, self.BACKUP_JOB_KIND):
                try:
                    metrics_list.append(await self._metrics_for_backup(deps=deps))
                except RuntimeError:
                    if resolved_kind == self.BACKUP_JOB_KIND:
                        raise

            if not metrics_list:
                raise RuntimeError("浠诲姟瀛樺偍鏈垵濮嬪寲")

            payload = metrics_list[0] if resolved_kind != self.ALL_KIND else self._merge_metrics(metrics_list)
            if cache_ttl_s > 0:
                _METRIC_SNAPSHOT_CACHE[resolved_kind] = (now_ts, copy.deepcopy(payload))

        thresholds = self._metric_thresholds()
        alerts = self._build_metric_alerts(task_kind=resolved_kind, metrics=payload, thresholds=thresholds)
        self._emit_alert_logs(alerts)
        payload["alert_thresholds"] = thresholds
        payload["alerts"] = alerts
        payload["has_alert"] = len(alerts) > 0
        return payload

    @staticmethod
    def _normalize_list_limit(limit: int | None) -> int:
        try:
            value = int(limit) if limit is not None else 50
        except Exception:
            value = 50
        return max(1, min(value, 200))

    @staticmethod
    def _task_sort_timestamp(payload: dict[str, Any]) -> int:
        for field in ("updated_at_ms", "finished_at_ms", "started_at_ms", "created_at_ms"):
            try:
                value = int(payload.get(field) or 0)
            except Exception:
                value = 0
            if value > 0:
                return value
        return 0

    @staticmethod
    def _supported_status_filters() -> set[str]:
        return {
            "pending",
            "running",
            "paused",
            "pausing",
            "canceling",
            "canceled",
            "completed",
            "failed",
        }

    @classmethod
    def _parse_status_filter(cls, status: str | None) -> set[str] | None:
        raw = str(status or "").strip()
        if not raw:
            return None
        values = {item.strip().lower() for item in raw.split(",") if item.strip()}
        if not values:
            return None
        invalid = values - cls._supported_status_filters()
        if invalid:
            raise RuntimeError(f"unsupported task status filter: {', '.join(sorted(invalid))}")
        return values

    @staticmethod
    def _apply_status_filter(task_payloads: list[dict[str, Any]], *, status_filter: set[str] | None) -> list[dict[str, Any]]:
        if not status_filter:
            return list(task_payloads)
        filtered: list[dict[str, Any]] = []
        for payload in task_payloads:
            status = str(payload.get("status") or "").strip().lower()
            if status in status_filter:
                filtered.append(payload)
        return filtered

    async def _list_nas_tasks(self, *, deps, ctx: AuthContext, limit: int) -> list[dict[str, Any]]:
        store = getattr(deps, "nas_task_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        nas_tasks = await asyncio.to_thread(store.list_tasks, limit=limit)
        payloads: list[dict[str, Any]] = []
        for task in nas_tasks:
            payloads.append(
                await self._get_task_payload_by_kind(
                    task.task_id,
                    deps=deps,
                    ctx=ctx,
                    resolved_kind=self.NAS_IMPORT_KIND,
                )
            )
        return payloads

    async def _list_backup_tasks(self, *, deps, limit: int) -> list[dict[str, Any]]:
        store = getattr(deps, "data_security_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        jobs = await asyncio.to_thread(store.list_jobs, limit=limit)
        return [self._with_kind(self._backup_task_payload(job), task_kind=self.BACKUP_JOB_KIND) for job in jobs]

    async def _list_download_tasks(
        self,
        *,
        deps,
        ctx: AuthContext,
        limit: int,
        task_kind: str,
        store_attr: str,
    ) -> list[dict[str, Any]]:
        store = getattr(deps, store_attr, None)
        if store is None:
            raise RuntimeError("task store not initialized")
        sessions = await asyncio.to_thread(store.list_sessions, limit=limit)
        payloads: list[dict[str, Any]] = []
        for session in sessions:
            payloads.append(
                await self._get_task_payload_by_kind(
                    str(getattr(session, "session_id", "") or ""),
                    deps=deps,
                    ctx=ctx,
                    resolved_kind=task_kind,
                )
            )
        return payloads

    async def _list_upload_tasks(self, *, deps, limit: int) -> list[dict[str, Any]]:
        store = getattr(deps, "kb_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        docs = await asyncio.to_thread(store.list_documents, None, None, None, None, limit)
        return [self._upload_task_payload(doc) for doc in docs]

    async def _list_paper_plag_tasks(self, *, deps, limit: int) -> list[dict[str, Any]]:
        store = self._paper_plag_store(deps)
        if store is None:
            raise RuntimeError("task store not initialized")
        reports = await asyncio.to_thread(store.list_reports, limit=limit, statuses=None, paper_id=None)
        return [self._paper_plag_task_payload(item) for item in reports]

    async def list_tasks(
        self,
        *,
        deps,
        ctx: AuthContext,
        task_kind: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        resolved_kind = self._resolve_metrics_kind(task_kind)
        safe_limit = self._normalize_list_limit(limit)
        status_filter = self._parse_status_filter(status)
        payloads: list[dict[str, Any]] = []
        active_sources = 0

        if resolved_kind in (self.ALL_KIND, self.NAS_IMPORT_KIND):
            if getattr(deps, "nas_task_store", None) is not None:
                active_sources += 1
                payloads.extend(await self._list_nas_tasks(deps=deps, ctx=ctx, limit=safe_limit))
            elif resolved_kind == self.NAS_IMPORT_KIND:
                raise RuntimeError("task store not initialized")

        if resolved_kind in (self.ALL_KIND, self.BACKUP_JOB_KIND):
            if getattr(deps, "data_security_store", None) is not None:
                active_sources += 1
                payloads.extend(await self._list_backup_tasks(deps=deps, limit=safe_limit))
            elif resolved_kind == self.BACKUP_JOB_KIND:
                raise RuntimeError("task store not initialized")

        if resolved_kind in (self.ALL_KIND, self.COLLECTION_KIND, self.PAPER_DOWNLOAD_KIND):
            if getattr(deps, "paper_download_store", None) is not None:
                active_sources += 1
                payloads.extend(
                    await self._list_download_tasks(
                        deps=deps,
                        ctx=ctx,
                        limit=safe_limit,
                        task_kind=self.PAPER_DOWNLOAD_KIND,
                        store_attr="paper_download_store",
                    )
                )
            elif resolved_kind == self.PAPER_DOWNLOAD_KIND:
                raise RuntimeError("task store not initialized")

        if resolved_kind in (self.ALL_KIND, self.COLLECTION_KIND, self.PATENT_DOWNLOAD_KIND):
            if getattr(deps, "patent_download_store", None) is not None:
                active_sources += 1
                payloads.extend(
                    await self._list_download_tasks(
                        deps=deps,
                        ctx=ctx,
                        limit=safe_limit,
                        task_kind=self.PATENT_DOWNLOAD_KIND,
                        store_attr="patent_download_store",
                    )
                )
            elif resolved_kind == self.PATENT_DOWNLOAD_KIND:
                raise RuntimeError("task store not initialized")

        if resolved_kind in (self.ALL_KIND, self.PAPER_PLAG_KIND):
            if self._paper_plag_store(deps) is not None:
                active_sources += 1
                payloads.extend(await self._list_paper_plag_tasks(deps=deps, limit=safe_limit))
            elif resolved_kind == self.PAPER_PLAG_KIND:
                raise RuntimeError("task store not initialized")

        if resolved_kind in (self.ALL_KIND, self.KNOWLEDGE_UPLOAD_KIND):
            if getattr(deps, "kb_store", None) is not None:
                active_sources += 1
                payloads.extend(await self._list_upload_tasks(deps=deps, limit=safe_limit))
            elif resolved_kind == self.KNOWLEDGE_UPLOAD_KIND:
                raise RuntimeError("task store not initialized")

        if active_sources <= 0:
            raise RuntimeError("task store not initialized")

        filtered = self._apply_status_filter(payloads, status_filter=status_filter)
        filtered.sort(key=self._task_sort_timestamp, reverse=True)
        tasks = filtered[:safe_limit]

        return {
            "task_kind": resolved_kind,
            "status_filter": sorted(status_filter) if status_filter else [],
            "limit": safe_limit,
            "total_tasks": len(tasks),
            "tasks": tasks,
        }

    @staticmethod
    def _upload_status_to_unified(status: str) -> str:
        mapping = {
            "pending": "pending",
            "approved": "completed",
            "rejected": "failed",
            "failed": "failed",
            "completed": "completed",
        }
        normalized = str(status or "").strip().lower()
        return mapping.get(normalized, normalized or "pending")

    @staticmethod
    def _paper_plag_status_to_unified(status: str) -> str:
        mapping = {
            "pending": "pending",
            "running": "running",
            "canceling": "canceling",
            "canceled": "canceled",
            "cancelled": "canceled",
            "completed": "completed",
            "failed": "failed",
        }
        normalized = str(status or "").strip().lower()
        return mapping.get(normalized, normalized or "pending")

    @classmethod
    def _paper_plag_task_payload(cls, report) -> dict[str, Any]:
        raw_status = str(getattr(report, "status", "") or "")
        unified_status = cls._paper_plag_status_to_unified(raw_status)
        duplicate_rate = float(getattr(report, "duplicate_rate", 0.0) or 0.0)
        score = float(getattr(report, "score", 0.0) or 0.0)
        progress = 0 if unified_status in ("pending", "running", "canceling") else 100
        return {
            "task_id": str(getattr(report, "report_id", "") or ""),
            "owner_user_id": str(getattr(report, "created_by_user_id", "") or ""),
            "task_priority": 100,
            "status": unified_status,
            "raw_status": raw_status,
            "progress_percent": progress,
            "remaining_percent": max(100 - progress, 0),
            "queue_position": None,
            "is_queued": unified_status == "pending",
            "max_concurrency": 1,
            "can_cancel": unified_status in ("pending", "running", "canceling"),
            "can_pause": False,
            "can_resume": False,
            "can_retry": False,
            "retry_count": 0,
            "quota": {
                "global_limit": 1,
                "task_kind_limit": 1,
                "per_user_limit": 1,
            },
            "quota_blocked_reason": None,
            "paper_id": str(getattr(report, "paper_id", "") or ""),
            "version_id": getattr(report, "version_id", None),
            "score": score,
            "duplicate_rate": duplicate_rate,
            "source_count": int(getattr(report, "source_count", 0) or 0),
            "summary": getattr(report, "summary", None),
            "report_file_path": getattr(report, "report_file_path", None),
            "created_at_ms": int(getattr(report, "created_at_ms", 0) or 0),
            "updated_at_ms": int(getattr(report, "updated_at_ms", 0) or 0),
            "finished_at_ms": getattr(report, "finished_at_ms", None),
            "task_kind": cls.PAPER_PLAG_KIND,
        }

    @classmethod
    def _upload_task_payload(cls, doc) -> dict[str, Any]:
        raw_status = str(getattr(doc, "status", "") or "")
        unified_status = cls._upload_status_to_unified(raw_status)
        progress = 0 if unified_status == "pending" else 100
        can_retry = unified_status == "failed"
        return {
            "task_id": str(getattr(doc, "doc_id", "") or ""),
            "owner_user_id": str(getattr(doc, "uploaded_by", "") or ""),
            "task_priority": 100,
            "status": unified_status,
            "raw_status": raw_status,
            "progress_percent": progress,
            "remaining_percent": max(100 - progress, 0),
            "queue_position": None,
            "is_queued": unified_status == "pending",
            "max_concurrency": 1,
            "can_cancel": False,
            "can_pause": False,
            "can_resume": False,
            "can_retry": can_retry,
            "retry_count": 0,
            "quota": {
                "global_limit": 1,
                "task_kind_limit": 1,
                "per_user_limit": 1,
            },
            "quota_blocked_reason": None,
            "filename": str(getattr(doc, "filename", "") or ""),
            "file_size": int(getattr(doc, "file_size", 0) or 0),
            "mime_type": str(getattr(doc, "mime_type", "") or ""),
            "kb_id": str(getattr(doc, "kb_name", "") or getattr(doc, "kb_id", "") or ""),
            "reviewed_by": getattr(doc, "reviewed_by", None),
            "reviewed_at_ms": getattr(doc, "reviewed_at_ms", None),
            "review_notes": getattr(doc, "review_notes", None),
            "error": getattr(doc, "review_notes", None) if unified_status == "failed" else None,
            "created_at_ms": int(getattr(doc, "uploaded_at_ms", 0) or 0),
            "updated_at_ms": int(
                getattr(doc, "reviewed_at_ms", 0) or getattr(doc, "uploaded_at_ms", 0) or 0
            ),
            "task_kind": cls.KNOWLEDGE_UPLOAD_KIND,
        }

    @staticmethod
    def _download_status_to_unified(status: str) -> str:
        mapping = {
            "queued": "pending",
            "pending": "pending",
            "running": "running",
            "stopping": "canceling",
            "canceling": "canceling",
            "stopped": "canceled",
            "canceled": "canceled",
            "cancelled": "canceled",
            "completed": "completed",
            "failed": "failed",
        }
        normalized = str(status or "").strip().lower()
        return mapping.get(normalized, normalized or "pending")

    @staticmethod
    def _is_downloaded_item_status(status: str | None) -> bool:
        normalized = str(status or "").strip().lower()
        return normalized in ("downloaded", "downloaded_cached")

    @classmethod
    def _download_task_payload(
        cls,
        *,
        task_id: str,
        task_kind: str,
        session_data: dict[str, Any],
        item_count: int,
        downloaded_count: int,
    ) -> dict[str, Any]:
        unified_status = cls._download_status_to_unified(str(session_data.get("status") or ""))
        if item_count > 0:
            progress = int(max(0, min(100, round(float(downloaded_count) * 100.0 / float(item_count)))))
        elif unified_status in ("completed", "failed", "canceled"):
            progress = 100
        else:
            progress = 0
        failed_items = max(int(item_count) - int(downloaded_count), 0)
        can_cancel = unified_status in ("pending", "running", "canceling")
        return {
            "task_id": str(task_id),
            "owner_user_id": str(session_data.get("created_by") or ""),
            "task_priority": 100,
            "status": unified_status,
            "raw_status": str(session_data.get("status") or ""),
            "progress_percent": progress,
            "remaining_percent": max(100 - progress, 0),
            "queue_position": None,
            "is_queued": unified_status == "pending",
            "max_concurrency": 1,
            "can_cancel": can_cancel,
            "can_pause": False,
            "can_resume": False,
            "can_retry": False,
            "retry_count": 0,
            "quota": {
                "global_limit": 1,
                "task_kind_limit": 1,
                "per_user_limit": 1,
            },
            "quota_blocked_reason": None,
            "keyword_text": str(session_data.get("keyword_text") or ""),
            "keywords": list(session_data.get("keywords") or []),
            "use_and": bool(session_data.get("use_and") or False),
            "sources": dict(session_data.get("sources") or {}),
            "source_errors": dict(session_data.get("source_errors") or {}),
            "source_stats": dict(session_data.get("source_stats") or {}),
            "error": session_data.get("error"),
            "created_at_ms": int(session_data.get("created_at_ms") or 0),
            "total_items": int(item_count),
            "downloaded_items": int(downloaded_count),
            "failed_items": int(failed_items),
            "task_kind": str(task_kind),
        }

    async def _get_paper_task_payload(self, task_id: str, *, deps) -> dict[str, Any]:
        store = getattr(deps, "paper_download_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        session_id = str(task_id or "").strip()
        session = await asyncio.to_thread(store.get_session, session_id)
        if session is None:
            raise RuntimeError("task not found")
        items = await asyncio.to_thread(store.list_items, session_id=session_id)
        downloaded_count = sum(
            1 for item in items if self._is_downloaded_item_status(getattr(item, "status", None))
        )
        session_data = paper_session_to_dict(session)
        self._remember_task_kind(task_id, task_kind=self.PAPER_DOWNLOAD_KIND)
        return self._download_task_payload(
            task_id=session_id,
            task_kind=self.PAPER_DOWNLOAD_KIND,
            session_data=session_data,
            item_count=len(items),
            downloaded_count=downloaded_count,
        )

    async def _get_patent_task_payload(self, task_id: str, *, deps) -> dict[str, Any]:
        store = getattr(deps, "patent_download_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        session_id = str(task_id or "").strip()
        session = await asyncio.to_thread(store.get_session, session_id)
        if session is None:
            raise RuntimeError("task not found")
        items = await asyncio.to_thread(store.list_items, session_id=session_id)
        downloaded_count = sum(
            1 for item in items if self._is_downloaded_item_status(getattr(item, "status", None))
        )
        session_data = patent_session_to_dict(session)
        self._remember_task_kind(task_id, task_kind=self.PATENT_DOWNLOAD_KIND)
        return self._download_task_payload(
            task_id=session_id,
            task_kind=self.PATENT_DOWNLOAD_KIND,
            session_data=session_data,
            item_count=len(items),
            downloaded_count=downloaded_count,
        )

    async def _get_upload_task_payload(self, task_id: str, *, deps) -> dict[str, Any]:
        store = getattr(deps, "kb_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        normalized_task_id = str(task_id or "").strip()
        doc = await asyncio.to_thread(store.get_document, normalized_task_id)
        if doc is None:
            raise RuntimeError("task not found")
        self._remember_task_kind(normalized_task_id, task_kind=self.KNOWLEDGE_UPLOAD_KIND)
        return self._upload_task_payload(doc)

    async def _get_paper_plag_task_payload(self, task_id: str, *, deps) -> dict[str, Any]:
        store = self._paper_plag_store(deps)
        if store is None:
            raise RuntimeError("task store not initialized")
        normalized_task_id = str(task_id or "").strip()
        report = await asyncio.to_thread(store.get_report, normalized_task_id)
        if report is None:
            raise RuntimeError("task not found")
        self._remember_task_kind(normalized_task_id, task_kind=self.PAPER_PLAG_KIND)
        return self._paper_plag_task_payload(report)

    async def _get_task_payload_by_kind(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext,
        resolved_kind: str,
    ) -> dict[str, Any]:
        normalized_task_id = str(task_id or "").strip()
        cached_payload = self._read_cached_task_payload(task_id=normalized_task_id, task_kind=resolved_kind)
        if cached_payload is not None:
            self._remember_task_kind(normalized_task_id, task_kind=resolved_kind)
            return cached_payload

        async def _fetch_payload_uncached() -> dict[str, Any]:
            if resolved_kind == self.NAS_IMPORT_KIND:
                payload = await self._get_nas_task_payload(normalized_task_id, deps=deps, ctx=ctx)
            elif resolved_kind == self.BACKUP_JOB_KIND:
                payload = await self._get_backup_task_payload(normalized_task_id, deps=deps)
            elif resolved_kind == self.PAPER_DOWNLOAD_KIND:
                payload = await self._get_paper_task_payload(normalized_task_id, deps=deps)
            elif resolved_kind == self.PATENT_DOWNLOAD_KIND:
                payload = await self._get_patent_task_payload(normalized_task_id, deps=deps)
            elif resolved_kind == self.PAPER_PLAG_KIND:
                payload = await self._get_paper_plag_task_payload(normalized_task_id, deps=deps)
            elif resolved_kind == self.KNOWLEDGE_UPLOAD_KIND:
                payload = await self._get_upload_task_payload(normalized_task_id, deps=deps)
            else:
                raise RuntimeError(f"unsupported task kind: {resolved_kind}")
            return self._with_kind(payload, task_kind=resolved_kind)

        cache_ttl_s = self._task_payload_cache_ttl_seconds()
        if cache_ttl_s > 0:
            lock_key = self._task_payload_cache_key(task_id=normalized_task_id, task_kind=resolved_kind)
            lock = _TASK_PAYLOAD_FETCH_LOCKS.setdefault(lock_key, asyncio.Lock())
            async with lock:
                cached_payload = self._read_cached_task_payload(task_id=normalized_task_id, task_kind=resolved_kind)
                if cached_payload is not None:
                    self._remember_task_kind(normalized_task_id, task_kind=resolved_kind)
                    return cached_payload
                payload_with_kind = await _fetch_payload_uncached()
                self._remember_task_kind(normalized_task_id, task_kind=resolved_kind)
                self._remember_task_payload(
                    task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
                )
                return payload_with_kind

        payload_with_kind = await _fetch_payload_uncached()
        self._remember_task_kind(normalized_task_id, task_kind=resolved_kind)
        return payload_with_kind

    @staticmethod
    def _raise_runtime_from_external_error(exc: Exception) -> None:
        status_code = int(getattr(exc, "status_code", 0) or 0)
        detail = str(getattr(exc, "detail", "") or str(exc or "")).strip()
        lowered = detail.lower()
        if status_code == 404 or "not found" in lowered or "not_found" in lowered:
            raise RuntimeError("task not found") from exc
        raise RuntimeError(detail or "task operation failed") from exc

    async def _metrics_for_download_sessions(
        self,
        *,
        deps,
        store_attr: str,
        task_kind: str,
        limit: int = 500,
    ) -> dict[str, Any]:
        store = getattr(deps, store_attr, None)
        if store is None:
            raise RuntimeError("task store not initialized")
        sessions = await asyncio.to_thread(store.list_sessions, limit=max(1, min(2000, int(limit))))
        total_tasks = len(sessions)
        failed_tasks = 0
        backlog_tasks = 0
        status_counts: dict[str, int] = defaultdict(int)

        for session in sessions:
            status = self._download_status_to_unified(getattr(session, "status", ""))
            status_counts[status] += 1
            if status == "failed":
                failed_tasks += 1
            if status in ("pending", "running", "canceling"):
                backlog_tasks += 1

        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)
        return {
            "task_kind": task_kind,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": backlog_tasks,
            "avg_duration_ms": 0,
            "failure_rate": failure_rate,
            "status_counts": dict(status_counts),
        }

    async def _metrics_for_upload_tasks(self, *, deps, limit: int = 500) -> dict[str, Any]:
        store = getattr(deps, "kb_store", None)
        if store is None:
            raise RuntimeError("task store not initialized")
        docs = await asyncio.to_thread(store.list_documents, None, None, None, None, max(1, min(2000, int(limit))))
        total_tasks = len(docs)
        failed_tasks = 0
        backlog_tasks = 0
        status_counts: dict[str, int] = defaultdict(int)
        durations: list[int] = []

        for doc in docs:
            status = self._upload_status_to_unified(str(getattr(doc, "status", "") or ""))
            status_counts[status] += 1
            if status == "failed":
                failed_tasks += 1
            if status == "pending":
                backlog_tasks += 1
            if status in ("completed", "failed"):
                created_at = int(getattr(doc, "uploaded_at_ms", 0) or 0)
                finished_at = int(getattr(doc, "reviewed_at_ms", 0) or 0)
                if created_at > 0 and finished_at >= created_at:
                    durations.append(finished_at - created_at)

        avg_duration_ms = int(sum(durations) / len(durations)) if durations else 0
        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)
        return {
            "task_kind": self.KNOWLEDGE_UPLOAD_KIND,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": backlog_tasks,
            "avg_duration_ms": avg_duration_ms,
            "failure_rate": failure_rate,
            "status_counts": dict(status_counts),
        }

    async def _metrics_for_paper_plag_tasks(self, *, deps, limit: int = 500) -> dict[str, Any]:
        store = self._paper_plag_store(deps)
        if store is None:
            raise RuntimeError("task store not initialized")
        reports = await asyncio.to_thread(
            store.list_reports,
            limit=max(1, min(2000, int(limit))),
            statuses=None,
            paper_id=None,
        )
        total_tasks = len(reports)
        failed_tasks = 0
        backlog_tasks = 0
        status_counts: dict[str, int] = defaultdict(int)
        durations: list[int] = []

        for report in reports:
            status = self._paper_plag_status_to_unified(str(getattr(report, "status", "") or ""))
            status_counts[status] += 1
            if status == "failed":
                failed_tasks += 1
            if status in ("pending", "running", "canceling"):
                backlog_tasks += 1
            if status in ("completed", "failed", "canceled"):
                created_at = int(getattr(report, "created_at_ms", 0) or 0)
                finished_at = int(getattr(report, "finished_at_ms", 0) or 0)
                if created_at > 0 and finished_at >= created_at:
                    durations.append(finished_at - created_at)

        avg_duration_ms = int(sum(durations) / len(durations)) if durations else 0
        failure_rate = 0.0 if total_tasks <= 0 else round(failed_tasks / total_tasks, 4)
        return {
            "task_kind": self.PAPER_PLAG_KIND,
            "total_tasks": total_tasks,
            "failed_tasks": failed_tasks,
            "backlog_tasks": backlog_tasks,
            "avg_duration_ms": avg_duration_ms,
            "failure_rate": failure_rate,
            "status_counts": dict(status_counts),
        }

    async def get_task(self, task_id: str, *, deps, ctx: AuthContext, task_kind: str | None = None) -> dict[str, Any]:
        normalized_kind = str(task_kind or self.AUTO_KIND).strip().lower()
        if normalized_kind == self.COLLECTION_KIND:
            resolved_collection_kind = await self._resolve_collection_task_kind(task_id, deps=deps)
            return await self._get_task_payload_by_kind(
                task_id,
                deps=deps,
                ctx=ctx,
                resolved_kind=resolved_collection_kind,
            )
        supported_kinds = (
            self.NAS_IMPORT_KIND,
            self.BACKUP_JOB_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        )

        if normalized_kind in supported_kinds:
            return await self._get_task_payload_by_kind(task_id, deps=deps, ctx=ctx, resolved_kind=normalized_kind)
        if normalized_kind not in (self.AUTO_KIND, self.ALL_KIND):
            raise RuntimeError(f"unsupported task kind: {normalized_kind}")

        cached_kind = self._read_cached_task_kind(task_id)
        if cached_kind in supported_kinds:
            try:
                return await self._get_task_payload_by_kind(task_id, deps=deps, ctx=ctx, resolved_kind=cached_kind)
            except RuntimeError as exc:
                if not self._is_not_found_error(exc):
                    raise
                _TASK_KIND_CACHE.pop(str(task_id or "").strip(), None)

        for candidate_kind in self._candidate_kinds_for_task_id(task_id):
            try:
                return await self._get_task_payload_by_kind(task_id, deps=deps, ctx=ctx, resolved_kind=candidate_kind)
            except RuntimeError as exc:
                if not self._is_not_found_error(exc):
                    raise
                continue
        raise RuntimeError("task not found")

    async def pause_task(self, task_id: str, *, deps, task_kind: str | None = None) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        normalized_task_id = str(task_id or "").strip()
        if resolved_kind == self.NAS_IMPORT_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.pause_folder_import_task(normalized_task_id, deps=deps)
            payload_with_kind = self._with_kind(payload, task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind in (
            self.BACKUP_JOB_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        ):
            raise RuntimeError(f"task kind does not support pause: {resolved_kind}")
        raise RuntimeError(f"unsupported task kind: {resolved_kind}")

    async def resume_task(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext,
        task_kind: str | None = None,
    ) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        normalized_task_id = str(task_id or "").strip()
        if resolved_kind == self.NAS_IMPORT_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.resume_folder_import_task(normalized_task_id, deps=deps, ctx=ctx)
            payload_with_kind = self._with_kind(payload, task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind in (
            self.BACKUP_JOB_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
            self.KNOWLEDGE_UPLOAD_KIND,
        ):
            raise RuntimeError(f"task kind does not support resume: {resolved_kind}")
        raise RuntimeError(f"unsupported task kind: {resolved_kind}")

    async def cancel_task(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext | None = None,
        task_kind: str | None = None,
    ) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        normalized_task_id = str(task_id or "").strip()
        if resolved_kind == self.NAS_IMPORT_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.cancel_folder_import_task(normalized_task_id, deps=deps)
            payload_with_kind = self._with_kind(payload, task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind == self.BACKUP_JOB_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            store = getattr(deps, "data_security_store", None)
            if store is None:
                raise RuntimeError("task store not initialized")
            job_id = self._parse_backup_job_id(normalized_task_id)
            try:
                job = await asyncio.to_thread(store.request_cancel_job, job_id)
            except Exception as exc:
                raise RuntimeError("task not found") from exc
            payload_with_kind = self._with_kind(self._backup_task_payload(job), task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind in (self.PAPER_DOWNLOAD_KIND, self.PATENT_DOWNLOAD_KIND):
            if ctx is None:
                raise RuntimeError("missing auth context")
            self._invalidate_task_payload_cache(normalized_task_id)
            manager = PaperDownloadManager(deps) if resolved_kind == self.PAPER_DOWNLOAD_KIND else PatentDownloadManager(deps)
            try:
                await asyncio.to_thread(manager.stop_session_download, session_id=normalized_task_id, ctx=ctx)
            except Exception as exc:
                self._raise_runtime_from_external_error(exc)
            if resolved_kind == self.PAPER_DOWNLOAD_KIND:
                payload = await self._get_paper_task_payload(normalized_task_id, deps=deps)
            else:
                payload = await self._get_patent_task_payload(normalized_task_id, deps=deps)
            payload_with_kind = self._with_kind(payload, task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind == self.PAPER_PLAG_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            store = self._paper_plag_store(deps)
            if store is None:
                raise RuntimeError("task store not initialized")
            report = await asyncio.to_thread(store.request_cancel_report, normalized_task_id)
            if report is None:
                raise RuntimeError("task not found")
            if str(getattr(report, "status", "") or "").strip().lower() == "canceling":
                refreshed = await asyncio.to_thread(store.get_report, normalized_task_id)
                if refreshed is not None:
                    report = refreshed
            payload_with_kind = self._with_kind(self._paper_plag_task_payload(report), task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind == self.KNOWLEDGE_UPLOAD_KIND:
            raise RuntimeError(f"task kind does not support cancel: {resolved_kind}")
        raise RuntimeError(f"unsupported task kind: {resolved_kind}")

    async def retry_task(
        self,
        task_id: str,
        *,
        deps,
        ctx: AuthContext,
        task_kind: str | None = None,
    ) -> dict[str, Any]:
        resolved_kind = await self._resolve_kind(task_id, deps=deps, task_kind=task_kind)
        normalized_task_id = str(task_id or "").strip()
        if resolved_kind == self.NAS_IMPORT_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            service = NasBrowserService(task_store=deps.nas_task_store)
            payload = await service.retry_folder_import_task(normalized_task_id, deps=deps, ctx=ctx)
            payload_with_kind = self._with_kind(payload, task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        if resolved_kind in (
            self.BACKUP_JOB_KIND,
            self.PAPER_DOWNLOAD_KIND,
            self.PATENT_DOWNLOAD_KIND,
            self.PAPER_PLAG_KIND,
        ):
            raise RuntimeError(f"task kind does not support retry: {resolved_kind}")
        if resolved_kind == self.KNOWLEDGE_UPLOAD_KIND:
            self._invalidate_task_payload_cache(normalized_task_id)
            store = getattr(deps, "kb_store", None)
            if store is None:
                raise RuntimeError("task store not initialized")
            doc = await asyncio.to_thread(store.get_document, normalized_task_id)
            if doc is None:
                raise RuntimeError("task not found")
            current_status = self._upload_status_to_unified(str(getattr(doc, "status", "") or ""))
            if current_status != "failed":
                raise RuntimeError("task status does not support retry")
            updated = await asyncio.to_thread(store.requeue_document_for_retry, normalized_task_id)
            if updated is None:
                raise RuntimeError("task not found")
            payload_with_kind = self._with_kind(self._upload_task_payload(updated), task_kind=resolved_kind)
            self._remember_task_payload(
                task_id=normalized_task_id, task_kind=resolved_kind, payload=payload_with_kind
            )
            return payload_with_kind
        raise RuntimeError(f"unsupported task kind: {resolved_kind}")

    async def get_metrics(self, *, deps, task_kind: str | None = None) -> dict[str, Any]:
        resolved_kind = self._resolve_metrics_kind(task_kind)
        cache_ttl_s = self._metrics_cache_ttl_seconds()
        
        async def _build_metrics_payload() -> dict[str, Any]:
            metrics_list: list[dict[str, Any]] = []
            if resolved_kind == self.ALL_KIND:
                tasks: list[tuple[str, Any]] = []
                if getattr(deps, "nas_task_store", None) is not None:
                    tasks.append((self.NAS_IMPORT_KIND, self._metrics_for_nas(deps=deps)))
                if getattr(deps, "data_security_store", None) is not None:
                    tasks.append((self.BACKUP_JOB_KIND, self._metrics_for_backup(deps=deps)))
                if getattr(deps, "paper_download_store", None) is not None:
                    tasks.append(
                        (
                            self.PAPER_DOWNLOAD_KIND,
                            self._metrics_for_download_sessions(
                                deps=deps,
                                store_attr="paper_download_store",
                                task_kind=self.PAPER_DOWNLOAD_KIND,
                            ),
                        )
                    )
                if getattr(deps, "patent_download_store", None) is not None:
                    tasks.append(
                        (
                            self.PATENT_DOWNLOAD_KIND,
                            self._metrics_for_download_sessions(
                                deps=deps,
                                store_attr="patent_download_store",
                                task_kind=self.PATENT_DOWNLOAD_KIND,
                            ),
                        )
                    )
                if self._paper_plag_store(deps) is not None:
                    tasks.append(
                        (
                            self.PAPER_PLAG_KIND,
                            self._metrics_for_paper_plag_tasks(deps=deps),
                        )
                    )
                if getattr(deps, "kb_store", None) is not None:
                    tasks.append(
                        (
                            self.KNOWLEDGE_UPLOAD_KIND,
                            self._metrics_for_upload_tasks(deps=deps),
                        )
                    )

                if tasks:
                    results = await asyncio.gather(*(item[1] for item in tasks), return_exceptions=True)
                    for result in results:
                        if isinstance(result, RuntimeError):
                            continue
                        if isinstance(result, Exception):
                            raise result
                        metrics_list.append(result)
            elif resolved_kind == self.COLLECTION_KIND:
                tasks: list[Any] = []
                if getattr(deps, "paper_download_store", None) is not None:
                    tasks.append(
                        self._metrics_for_download_sessions(
                            deps=deps,
                            store_attr="paper_download_store",
                            task_kind=self.PAPER_DOWNLOAD_KIND,
                        )
                    )
                if getattr(deps, "patent_download_store", None) is not None:
                    tasks.append(
                        self._metrics_for_download_sessions(
                            deps=deps,
                            store_attr="patent_download_store",
                            task_kind=self.PATENT_DOWNLOAD_KIND,
                        )
                    )
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, RuntimeError):
                            continue
                        if isinstance(result, Exception):
                            raise result
                        metrics_list.append(result)
            elif resolved_kind == self.NAS_IMPORT_KIND:
                metrics_list.append(await self._metrics_for_nas(deps=deps))
            elif resolved_kind == self.BACKUP_JOB_KIND:
                metrics_list.append(await self._metrics_for_backup(deps=deps))
            elif resolved_kind == self.PAPER_DOWNLOAD_KIND:
                metrics_list.append(
                    await self._metrics_for_download_sessions(
                        deps=deps,
                        store_attr="paper_download_store",
                        task_kind=self.PAPER_DOWNLOAD_KIND,
                    )
                )
            elif resolved_kind == self.PATENT_DOWNLOAD_KIND:
                metrics_list.append(
                    await self._metrics_for_download_sessions(
                        deps=deps,
                        store_attr="patent_download_store",
                        task_kind=self.PATENT_DOWNLOAD_KIND,
                    )
                )
            elif resolved_kind == self.PAPER_PLAG_KIND:
                metrics_list.append(await self._metrics_for_paper_plag_tasks(deps=deps))
            elif resolved_kind == self.KNOWLEDGE_UPLOAD_KIND:
                metrics_list.append(await self._metrics_for_upload_tasks(deps=deps))

            if not metrics_list:
                raise RuntimeError("task store not initialized")
            if resolved_kind == self.ALL_KIND:
                return self._merge_metrics(metrics_list)
            if resolved_kind == self.COLLECTION_KIND:
                merged = self._merge_metrics(metrics_list)
                merged["task_kind"] = self.COLLECTION_KIND
                return merged
            return metrics_list[0]

        payload: dict[str, Any] | None = None
        if cache_ttl_s > 0:
            now_ts = time.monotonic()
            cached = _METRIC_SNAPSHOT_CACHE.get(resolved_kind)
            if cached and (now_ts - cached[0]) <= cache_ttl_s:
                payload = copy.deepcopy(cached[1])

        if payload is None and cache_ttl_s > 0:
            lock = _METRIC_FETCH_LOCKS.setdefault(resolved_kind, asyncio.Lock())
            async with lock:
                now_ts = time.monotonic()
                cached = _METRIC_SNAPSHOT_CACHE.get(resolved_kind)
                if cached and (now_ts - cached[0]) <= cache_ttl_s:
                    payload = copy.deepcopy(cached[1])
                else:
                    payload = await _build_metrics_payload()
                    _METRIC_SNAPSHOT_CACHE[resolved_kind] = (time.monotonic(), copy.deepcopy(payload))
        elif payload is None:
            payload = await _build_metrics_payload()

        thresholds = self._metric_thresholds()
        alerts = self._build_metric_alerts(task_kind=resolved_kind, metrics=payload, thresholds=thresholds)
        self._emit_alert_logs(alerts)
        payload["alert_thresholds"] = thresholds
        payload["alerts"] = alerts
        payload["has_alert"] = len(alerts) > 0
        return payload


