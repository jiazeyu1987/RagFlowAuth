from __future__ import annotations

import logging
import threading
import time

from backend.app.modules.data_security.runner import start_job_if_idle
from backend.services.data_security_store import DataSecurityStore

logger = logging.getLogger(__name__)


def start_data_security_scheduler(*, stop_event: threading.Event, poll_seconds: int = 10) -> threading.Thread:
    """
    Periodically checks settings and schedules backups.

    Notes:
    - Uses `data_security_settings.last_run_at_ms` to prevent repeated triggering.
    - If enabled and `last_run_at_ms` is NULL, it triggers a backup soon after startup.
    """

    def loop() -> None:
        logger.info("DataSecurity scheduler started (poll=%ss)", poll_seconds)
        store = DataSecurityStore()
        while not stop_event.is_set():
            try:
                settings = store.get_settings()
                if settings.enabled:
                    interval_minutes = max(1, int(settings.interval_minutes or 1440))
                    interval_ms = interval_minutes * 60 * 1000
                    now_ms = int(time.time() * 1000)
                    last_ms = settings.last_run_at_ms
                    due = last_ms is None or (now_ms - last_ms) >= interval_ms
                    if due:
                        store.touch_last_run(now_ms)
                        job_id = start_job_if_idle(reason="scheduled", store=store)
                        logger.info("DataSecurity scheduled backup job=%s", job_id)
            except Exception:
                logger.exception("DataSecurity scheduler tick failed")

            stop_event.wait(poll_seconds)

        logger.info("DataSecurity scheduler stopped")

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
