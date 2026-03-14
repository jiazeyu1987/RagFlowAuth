from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from backend.services.data_security_backup import DataSecurityBackupService
from backend.services.data_security_store import DataSecurityStore
from backend.services.nas_task_store import NasTaskStore
from backend.services.paper_download.store import PaperDownloadStore
from backend.services.patent_download.store import PatentDownloadStore
from backend.services.unified_task_quota_service import UnifiedTaskQuotaService

_lock = threading.Lock()
_running_job_id: int | None = None


def get_running_job_id() -> int | None:
    with _lock:
        return _running_job_id


def _start_backup_worker(*, job_id: int, full_backup: bool) -> None:
    def worker(target_job_id: int) -> None:
        global _running_job_id
        worker_store = DataSecurityStore()
        svc = DataSecurityBackupService(worker_store)
        try:
            if full_backup:
                svc.run_full_backup_job(target_job_id)
            else:
                svc.run_incremental_backup_job(target_job_id)
        except Exception as exc:
            now_ms = int(time.time() * 1000)
            worker_store.update_job(
                target_job_id,
                status="failed",
                progress=100,
                message="backup_failed",
                detail=str(exc),
                finished_at_ms=now_ms,
            )
        finally:
            with _lock:
                _running_job_id = None
            try:
                worker_store.release_backup_lock()
            except Exception:
                pass

    # Use non-daemon thread so backup can finish in container runtime.
    thread = threading.Thread(target=worker, args=(int(job_id),), daemon=False)
    thread.start()


def start_job_if_idle(
    *,
    reason: str,
    full_backup: bool = False,
    recover_active: bool = False,
    actor_user_id: str | None = None,
) -> int:
    """
    Start a backup job if none is running. Returns the job_id (existing or new).

    Args:
        reason: Reason for starting the job.
        full_backup: If True, run a full backup including Docker images and configs.
        recover_active: If True, resume persisted queued/running job on startup.
    """
    global _running_job_id
    store = DataSecurityStore()

    if not recover_active:
        try:
            db_path = str(getattr(store, "db_path", "") or "")
            quota_deps = SimpleNamespace(
                data_security_store=store,
                nas_task_store=NasTaskStore(db_path=db_path),
                paper_download_store=PaperDownloadStore(db_path=db_path),
                patent_download_store=PatentDownloadStore(db_path=db_path),
            )
            UnifiedTaskQuotaService().assert_can_start(
                deps=quota_deps,
                actor_user_id=actor_user_id,
                task_kind=UnifiedTaskQuotaService.BACKUP_KIND,
            )
        except RuntimeError:
            raise
        except Exception:
            # Keep backward compatibility when quota dependencies are unavailable.
            pass

    active_job_id = store.get_active_job_id()
    if active_job_id is not None:
        if not recover_active:
            return active_job_id
        active_job = store.get_job(active_job_id)
        active_status = str(getattr(active_job, "status", "") or "").strip().lower()
        if active_status == "canceling":
            store.mark_job_canceled(
                int(active_job_id),
                message="converged_after_restart",
                detail="startup_recovery",
            )
            return int(active_job_id)
        if active_status in ("queued", "running"):
            with _lock:
                if _running_job_id is not None:
                    return _running_job_id
            if not store.try_acquire_backup_lock(job_id=int(active_job_id)):
                return int(active_job_id)
            with _lock:
                if _running_job_id is not None:
                    try:
                        store.release_backup_lock()
                    except Exception:
                        pass
                    return _running_job_id
                _running_job_id = int(active_job_id)
            _start_backup_worker(job_id=int(active_job_id), full_backup=(str(active_job.kind or "") == "full"))
            return int(active_job_id)
        return int(active_job_id)

    with _lock:
        if _running_job_id is not None:
            return _running_job_id

    # Cross-process guard (multi-instance): ensure only one backup starts at a time.
    if not store.try_acquire_backup_lock():
        active_job_id = store.get_active_job_id()
        if active_job_id is not None:
            return int(active_job_id)
        # Lock exists but no active job is visible, try once to clear stale lock.
        try:
            store.release_backup_lock()
        except Exception:
            pass
        if not store.try_acquire_backup_lock():
            raise RuntimeError("backup_job_locked_by_other_process")

    with _lock:
        if _running_job_id is not None:
            try:
                store.release_backup_lock()
            except Exception:
                pass
            return _running_job_id

        kind = "full" if full_backup else "incremental"
        job = store.create_job_v2(kind=kind, status="queued", message=f"queued({reason})")
        _running_job_id = int(job.id)

    _start_backup_worker(job_id=int(job.id), full_backup=bool(full_backup))
    return int(job.id)


def recover_startup_jobs(*, limit: int = 10) -> dict[str, int]:
    """
    Recover backup jobs left in active states after restart.
    """
    store = DataSecurityStore()
    jobs = store.list_jobs(limit=max(1, min(int(limit), 200)))
    summary = {
        "scanned": 0,
        "resumed": 0,
        "canceled": 0,
        "failed": 0,
    }

    active_jobs = []
    for job in jobs:
        status = str(getattr(job, "status", "") or "").strip().lower()
        if status not in ("queued", "running", "canceling"):
            continue
        summary["scanned"] += 1
        if status == "canceling":
            try:
                store.mark_job_canceled(
                    int(job.id),
                    message="converged_after_restart",
                    detail="startup_recovery",
                )
                summary["canceled"] += 1
            except Exception:
                now_ms = int(time.time() * 1000)
                store.update_job(
                    int(job.id),
                    status="failed",
                    progress=100,
                    message="startup_recovery_failed",
                    detail="cancel_converge_failed",
                    finished_at_ms=now_ms,
                )
                summary["failed"] += 1
            continue
        active_jobs.append(job)

    resumed_job_id: int | None = None
    if active_jobs:
        try:
            resumed_job_id = int(start_job_if_idle(reason="startup_recovery", recover_active=True))
            summary["resumed"] += 1
        except Exception:
            resumed_job_id = None

    for job in active_jobs:
        if resumed_job_id is not None and int(job.id) == resumed_job_id:
            continue
        # Converge duplicate active jobs to failed to avoid indefinite backlog.
        now_ms = int(time.time() * 1000)
        store.update_job(
            int(job.id),
            status="failed",
            progress=100,
            message="startup_recovery_failed",
            detail="duplicate_active_job",
            finished_at_ms=now_ms,
        )
        summary["failed"] += 1

    return summary
