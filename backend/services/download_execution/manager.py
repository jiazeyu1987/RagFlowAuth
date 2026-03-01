from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

from backend.app.core.paths import resolve_repo_path


class DownloadExecutionManager:
    _registry_lock = threading.Lock()
    _jobs: dict[str, dict[str, threading.Thread]] = {}
    _cancelled_sessions: dict[str, set[str]] = {}
    _stop_requested_sessions: dict[str, set[str]] = {}

    def __init__(self, *, namespace: str):
        self.namespace = str(namespace or "").strip() or "download"

    @classmethod
    def _ns_jobs(cls, namespace: str) -> dict[str, threading.Thread]:
        return cls._jobs.setdefault(namespace, {})

    @classmethod
    def _ns_cancelled(cls, namespace: str) -> set[str]:
        return cls._cancelled_sessions.setdefault(namespace, set())

    @classmethod
    def _ns_stopped(cls, namespace: str) -> set[str]:
        return cls._stop_requested_sessions.setdefault(namespace, set())

    def normalize_source_configs(
        self,
        *,
        source_configs: dict[str, Any] | None,
        source_keys: tuple[str, ...] | list[str],
        default_limit: int,
        max_limit: int = 1000,
    ) -> dict[str, dict[str, Any]]:
        src = source_configs if isinstance(source_configs, dict) else {}
        out: dict[str, dict[str, Any]] = {}
        for key in source_keys:
            cfg = src.get(key)
            if not isinstance(cfg, dict):
                cfg = {}
            enabled = bool(cfg.get("enabled", False))
            limit = int(cfg.get("limit", default_limit) or default_limit)
            out[str(key)] = {"enabled": enabled, "limit": max(1, min(limit, max_limit))}
        return out

    def build_source_stats(
        self,
        *,
        enabled_sources: list[str],
        source_cfg: dict[str, dict[str, Any]],
        default_limit: int,
    ) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "requested_limit": int(source_cfg.get(key, {}).get("limit", default_limit) or default_limit),
                "candidates": 0,
                "downloaded": 0,
                "reused": 0,
                "failed": 0,
                "skipped_keyword": 0,
                "skipped_duplicate": 0,
                "skipped_stopped": 0,
                "failed_reasons": {},
            }
            for key in enabled_sources
        }

    def download_root(self, *, setting_value: str | None, fallback_dir: str) -> Path:
        root = resolve_repo_path(setting_value or fallback_dir)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def session_dir(self, *, root: Path, actor_id: str, session_id: str) -> Path:
        path = root / str(actor_id) / str(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def register_job(self, *, session_id: str, job: threading.Thread) -> None:
        with self._registry_lock:
            self._ns_jobs(self.namespace)[session_id] = job
            self._ns_cancelled(self.namespace).discard(session_id)
            self._ns_stopped(self.namespace).discard(session_id)

    def cancel_job(self, *, session_id: str) -> threading.Thread | None:
        with self._registry_lock:
            self._ns_cancelled(self.namespace).add(session_id)
            return self._ns_jobs(self.namespace).get(session_id)

    def is_cancelled(self, *, session_id: str) -> bool:
        with self._registry_lock:
            return session_id in self._ns_cancelled(self.namespace)

    def request_stop(self, *, session_id: str) -> threading.Thread | None:
        with self._registry_lock:
            self._ns_stopped(self.namespace).add(session_id)
            return self._ns_jobs(self.namespace).get(session_id)

    def is_stop_requested(self, *, session_id: str) -> bool:
        with self._registry_lock:
            return session_id in self._ns_stopped(self.namespace)

    def finish_job(self, *, session_id: str) -> None:
        with self._registry_lock:
            self._ns_jobs(self.namespace).pop(session_id, None)
            self._ns_cancelled(self.namespace).discard(session_id)
            self._ns_stopped(self.namespace).discard(session_id)

    def start_job(
        self,
        *,
        session_id: str,
        target: Callable[..., Any],
        kwargs: dict[str, Any],
        name_prefix: str,
    ) -> threading.Thread:
        worker = threading.Thread(
            target=target,
            kwargs=kwargs,
            daemon=True,
            name=f"{name_prefix}-{str(session_id)[:8]}",
        )
        self.register_job(session_id=session_id, job=worker)
        worker.start()
        return worker
