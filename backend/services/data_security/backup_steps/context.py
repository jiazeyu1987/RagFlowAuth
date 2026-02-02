from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.data_security_store import DataSecuritySettings, DataSecurityStore


class BackupCancelledError(RuntimeError):
    pass


@dataclass
class BackupContext:
    store: DataSecurityStore
    job_id: int
    settings: DataSecuritySettings
    include_images: bool
    job_kind: str | None = None

    target: str | None = None
    pack_dir: Path | None = None
    compose_file: Path | None = None
    ragflow_project: str | None = None

    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def update(self, *, message: str, progress: int | None = None, **kwargs: Any) -> None:
        payload: dict[str, Any] = {"message": message}
        if progress is not None:
            payload["progress"] = int(progress)
        payload.update(kwargs)
        self.store.update_job(self.job_id, **payload)

    def raise_if_cancelled(self) -> None:
        try:
            if self.store.is_cancel_requested(self.job_id):
                raise BackupCancelledError("backup_cancel_requested")
        except BackupCancelledError:
            raise
        except Exception:
            # Cancellation is best-effort; do not fail due to cancellation check errors.
            return
