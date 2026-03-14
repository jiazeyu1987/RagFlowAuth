from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.core.config import settings
from backend.services.paper_plag_store import PaperPlagStore


@dataclass(frozen=True)
class QuotaSnapshot:
    global_active: int
    user_active: int
    active_by_kind: dict[str, int]
    global_limit: int
    user_limit: int
    task_kind_limit: int


class UnifiedTaskQuotaService:
    NAS_KIND = "nas_import"
    BACKUP_KIND = "backup_job"
    COLLECTION_KIND = "collection"
    PAPER_KIND = "paper_download"
    PATENT_KIND = "patent_download"
    PAPER_PLAG_KIND = "paper_plagiarism"
    UPLOAD_KIND = "knowledge_upload"

    _NAS_ACTIVE = {"pending", "running", "pausing", "canceling"}
    _BACKUP_ACTIVE = {"queued", "running", "canceling"}
    _DOWNLOAD_ACTIVE = {"queued", "pending", "running", "stopping", "canceling"}
    _PAPER_PLAG_ACTIVE = {"pending", "running", "canceling"}

    @staticmethod
    def _safe_limit(value: Any) -> int:
        try:
            parsed = int(value)
        except Exception:
            return 0
        return max(0, parsed)

    @classmethod
    def _task_kind_limit(cls, task_kind: str) -> int:
        kind = str(task_kind or "").strip().lower()
        if kind == cls.NAS_KIND:
            return cls._safe_limit(getattr(settings, "TASK_NAS_CONCURRENCY_LIMIT", 0))
        if kind == cls.BACKUP_KIND:
            return cls._safe_limit(getattr(settings, "TASK_BACKUP_CONCURRENCY_LIMIT", 0))
        if kind == cls.COLLECTION_KIND:
            return cls._safe_limit(getattr(settings, "TASK_COLLECTION_CONCURRENCY_LIMIT", 0))
        if kind == cls.PAPER_KIND:
            return cls._safe_limit(getattr(settings, "TASK_PAPER_DOWNLOAD_CONCURRENCY_LIMIT", 0))
        if kind == cls.PATENT_KIND:
            return cls._safe_limit(getattr(settings, "TASK_PATENT_DOWNLOAD_CONCURRENCY_LIMIT", 0))
        if kind == cls.PAPER_PLAG_KIND:
            return cls._safe_limit(getattr(settings, "TASK_PAPER_PLAG_CONCURRENCY_LIMIT", 0))
        if kind == cls.UPLOAD_KIND:
            return cls._safe_limit(getattr(settings, "TASK_UPLOAD_CONCURRENCY_LIMIT", 0))
        return 0

    @classmethod
    def _count_nas_tasks(cls, *, deps, actor_user_id: str | None) -> tuple[int, int]:
        store = getattr(deps, "nas_task_store", None)
        if store is None or not hasattr(store, "list_tasks"):
            return 0, 0
        try:
            tasks = store.list_tasks(limit=2000, statuses=list(cls._NAS_ACTIVE))
        except Exception:
            return 0, 0
        total = len(tasks)
        if not actor_user_id:
            return total, 0
        user_count = sum(1 for item in tasks if str(getattr(item, "created_by_user_id", "") or "") == actor_user_id)
        return total, user_count

    @classmethod
    def _count_backup_jobs(cls, *, deps, actor_user_id: str | None) -> tuple[int, int]:
        del actor_user_id  # backup jobs currently system-owned
        store = getattr(deps, "data_security_store", None)
        if store is None or not hasattr(store, "list_jobs"):
            return 0, 0
        try:
            jobs = store.list_jobs(limit=2000)
        except Exception:
            return 0, 0
        total = 0
        for item in jobs:
            status = str(getattr(item, "status", "") or "").strip().lower()
            if status in cls._BACKUP_ACTIVE:
                total += 1
        return total, 0

    @classmethod
    def _count_download_sessions(
        cls,
        *,
        deps,
        actor_user_id: str | None,
        store_attr: str,
    ) -> tuple[int, int]:
        store = getattr(deps, store_attr, None)
        if store is None or not hasattr(store, "list_sessions"):
            return 0, 0
        try:
            sessions = store.list_sessions(limit=2000)
        except Exception:
            return 0, 0
        total = 0
        user_count = 0
        for item in sessions:
            status = str(getattr(item, "status", "") or "").strip().lower()
            if status not in cls._DOWNLOAD_ACTIVE:
                continue
            total += 1
            if actor_user_id and str(getattr(item, "created_by", "") or "") == actor_user_id:
                user_count += 1
        return total, user_count

    @classmethod
    def _count_upload_tasks(cls, *, deps, actor_user_id: str | None) -> tuple[int, int]:
        store = getattr(deps, "kb_store", None)
        if store is None or not hasattr(store, "list_documents"):
            return 0, 0
        try:
            docs = store.list_documents(limit=2000)
        except Exception:
            return 0, 0
        total = 0
        user_count = 0
        for doc in docs:
            status = str(getattr(doc, "status", "") or "").strip().lower()
            if status != "pending":
                continue
            total += 1
            if actor_user_id and str(getattr(doc, "uploaded_by", "") or "") == actor_user_id:
                user_count += 1
        return total, user_count

    @classmethod
    def _resolve_paper_plag_store(cls, *, deps):
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
    def _count_paper_plag_reports(cls, *, deps, actor_user_id: str | None) -> tuple[int, int]:
        store = cls._resolve_paper_plag_store(deps=deps)
        if store is None or not hasattr(store, "list_reports"):
            return 0, 0
        try:
            reports = store.list_reports(limit=2000, statuses=list(cls._PAPER_PLAG_ACTIVE))
        except Exception:
            return 0, 0
        total = 0
        user_count = 0
        for item in reports:
            status = str(getattr(item, "status", "") or "").strip().lower()
            if status not in cls._PAPER_PLAG_ACTIVE:
                continue
            total += 1
            if actor_user_id and str(getattr(item, "created_by_user_id", "") or "") == actor_user_id:
                user_count += 1
        return total, user_count

    def snapshot(self, *, deps, actor_user_id: str | None, task_kind: str) -> QuotaSnapshot:
        actor = str(actor_user_id or "").strip() or None
        nas_total, nas_user = self._count_nas_tasks(deps=deps, actor_user_id=actor)
        backup_total, backup_user = self._count_backup_jobs(deps=deps, actor_user_id=actor)
        paper_total, paper_user = self._count_download_sessions(
            deps=deps,
            actor_user_id=actor,
            store_attr="paper_download_store",
        )
        patent_total, patent_user = self._count_download_sessions(
            deps=deps,
            actor_user_id=actor,
            store_attr="patent_download_store",
        )
        upload_total, upload_user = self._count_upload_tasks(
            deps=deps,
            actor_user_id=actor,
        )
        paper_plag_total, paper_plag_user = self._count_paper_plag_reports(
            deps=deps,
            actor_user_id=actor,
        )

        global_active = int(nas_total + backup_total + paper_total + patent_total + upload_total + paper_plag_total)
        user_active = int(nas_user + backup_user + paper_user + patent_user + upload_user + paper_plag_user)
        by_kind = {
            self.NAS_KIND: int(nas_total),
            self.BACKUP_KIND: int(backup_total),
            self.COLLECTION_KIND: int(paper_total + patent_total),
            self.PAPER_KIND: int(paper_total),
            self.PATENT_KIND: int(patent_total),
            self.PAPER_PLAG_KIND: int(paper_plag_total),
            self.UPLOAD_KIND: int(upload_total),
        }
        return QuotaSnapshot(
            global_active=global_active,
            user_active=user_active,
            active_by_kind=by_kind,
            global_limit=self._safe_limit(getattr(settings, "TASK_GLOBAL_CONCURRENCY_LIMIT", 0)),
            user_limit=self._safe_limit(getattr(settings, "TASK_USER_CONCURRENCY_LIMIT", 0)),
            task_kind_limit=self._task_kind_limit(task_kind),
        )

    def assert_can_start(self, *, deps, actor_user_id: str | None, task_kind: str) -> QuotaSnapshot:
        normalized_kind = str(task_kind or "").strip().lower()
        if normalized_kind not in {
            self.NAS_KIND,
            self.BACKUP_KIND,
            self.COLLECTION_KIND,
            self.PAPER_KIND,
            self.PATENT_KIND,
            self.PAPER_PLAG_KIND,
            self.UPLOAD_KIND,
        }:
            raise RuntimeError(f"unsupported_task_kind_for_quota:{normalized_kind}")

        snapshot = self.snapshot(deps=deps, actor_user_id=actor_user_id, task_kind=normalized_kind)

        if snapshot.global_limit > 0 and snapshot.global_active >= snapshot.global_limit:
            raise RuntimeError("task_quota_exceeded:global")
        if snapshot.task_kind_limit > 0 and int(snapshot.active_by_kind.get(normalized_kind, 0)) >= snapshot.task_kind_limit:
            raise RuntimeError(f"task_quota_exceeded:task_kind:{normalized_kind}")
        if normalized_kind in {self.PAPER_KIND, self.PATENT_KIND}:
            collection_limit = self._task_kind_limit(self.COLLECTION_KIND)
            collection_active = int(snapshot.active_by_kind.get(self.COLLECTION_KIND, 0))
            if collection_limit > 0 and collection_active >= collection_limit:
                raise RuntimeError(f"task_quota_exceeded:task_kind:{self.COLLECTION_KIND}")
        if snapshot.user_limit > 0 and snapshot.user_active >= snapshot.user_limit:
            raise RuntimeError("task_quota_exceeded:user")

        return snapshot
