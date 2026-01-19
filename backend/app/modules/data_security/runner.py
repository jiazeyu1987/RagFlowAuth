from __future__ import annotations

import threading
import time

from backend.services.data_security_backup import DataSecurityBackupService
from backend.services.data_security_store import DataSecurityStore

_lock = threading.Lock()
_running_job_id: int | None = None


def get_running_job_id() -> int | None:
    with _lock:
        return _running_job_id


def start_job_if_idle(*, reason: str) -> int:
    """
    Start a backup job if none is running. Returns the job_id (existing or new).
    """
    global _running_job_id
    store = DataSecurityStore()

    with _lock:
        if _running_job_id is not None:
            return _running_job_id

        job = store.create_job(status="queued", message=f"已排队（{reason}）")
        _running_job_id = job.id

    def worker(job_id: int) -> None:
        global _running_job_id
        worker_store = DataSecurityStore()
        svc = DataSecurityBackupService(worker_store)
        try:
            svc.run_job(job_id)
        except Exception as exc:
            now_ms = int(time.time() * 1000)
            worker_store.update_job(
                job_id,
                status="failed",
                progress=100,
                message="备份失败",
                detail=str(exc),
                finished_at_ms=now_ms,
            )
        finally:
            with _lock:
                _running_job_id = None

    threading.Thread(target=worker, args=(job.id,), daemon=True).start()
    return job.id

