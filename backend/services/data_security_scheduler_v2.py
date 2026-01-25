"""
Improved backup scheduler with cron-based scheduling.

Key points:
- Uses cron expressions from `data_security_settings` (incremental/full) to decide when to run.
- Uses "last successful backup time" to avoid repeated triggers after restarts.
- Avoids retry storms: on failure, it does not re-trigger again in the same schedule window
  (best-effort; guarded in-memory for the current process).
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from backend.app.modules.data_security.runner import start_job_if_idle
from backend.services.data_security_store import DataSecurityStore


logger = logging.getLogger(__name__)


class BackupSchedulerV2:
    """
    Improved background scheduler for automated backups.

    Runs scheduled backups based on cron expressions stored in settings.
    """

    def __init__(self, store: DataSecurityStore):
        """
        Args:
            store: DataSecurityStore instance
        """
        self.store = store
        self._running = False
        self._thread = None
        self._stop_event = None
        # Best-effort: prevent repeated triggers within the same schedule window on failures.
        self._last_incremental_attempt_ms: int = 0
        self._last_full_attempt_ms: int = 0

    def _latest_scheduled_time_ms(self, schedule: str, now: datetime) -> int | None:
        """
        Return the most recent scheduled time (<= now) that matches the 5-part cron expression.

        Cron format: "minute hour day month weekday" where each part is "*" or an integer.
        Weekday follows standard cron conventions: Sunday=0 (or 7), Monday=1 ... Saturday=6.

        Returns:
          - epoch milliseconds of the latest scheduled time within the current day
          - None if the schedule is invalid or no candidate exists for today
        """
        try:
            parts = str(schedule or "").strip().split()
            if len(parts) != 5:
                return None

            minute_s, hour_s, day_s, month_s, weekday_s = parts

            def parse_int_or_none(v: str, lo: int, hi: int) -> int | None:
                if v == "*":
                    return None
                n = int(v)
                if n < lo or n > hi:
                    raise ValueError(f"out of range: {v}")
                return n

            target_minute = parse_int_or_none(minute_s, 0, 59)
            target_hour = parse_int_or_none(hour_s, 0, 23)
            target_day = parse_int_or_none(day_s, 1, 31)
            target_month = parse_int_or_none(month_s, 1, 12)
            target_weekday = parse_int_or_none(weekday_s, 0, 7)
            if target_weekday == 7:
                target_weekday = 0

            hours = range(24) if target_hour is None else [target_hour]
            minutes = range(60) if target_minute is None else [target_minute]

            best_ts: float | None = None
            for h in hours:
                for m in minutes:
                    dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                    if dt > now:
                        continue
                    if target_day is not None and dt.day != target_day:
                        continue
                    if target_month is not None and dt.month != target_month:
                        continue
                    if target_weekday is not None:
                        # Python: Mon=0..Sun=6 -> Cron: Sun=0..Sat=6
                        dt_cron_weekday = (dt.weekday() + 1) % 7
                        if dt_cron_weekday != target_weekday:
                            continue
                    ts = dt.timestamp()
                    if best_ts is None or ts > best_ts:
                        best_ts = ts

            if best_ts is None:
                return None
            return int(best_ts * 1000)
        except Exception:
            return None

    def _has_running_backup(self) -> bool:
        """Check if there's already a backup job running."""
        try:
            now_ms = int(time.time() * 1000)
            stale_ms = 24 * 60 * 60 * 1000  # 24h
            jobs = self.store.list_jobs(limit=5)
            for job in jobs:
                if job.status in ["queued", "running"]:
                    base_ms = job.started_at_ms or job.created_at_ms
                    # If the process crashed, a job might be left in queued/running forever.
                    # Mark very old jobs as failed to avoid blocking future schedules.
                    if job.finished_at_ms is None and now_ms - int(base_ms) > stale_ms:
                        try:
                            self.store.update_job(
                                job.id,
                                status="failed",
                                progress=100,
                                message="备份任务超时已标记失败",
                                detail="stale job",
                                finished_at_ms=now_ms,
                            )
                        except Exception:
                            logger.error(f"Failed to mark stale job #{job.id} as failed", exc_info=True)
                        continue
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking running jobs: {e}")
            return False  # Conservative: assume no job running

    def _should_run_incremental_backup(self, settings) -> tuple[bool, str, int | None]:
        """
        Check if incremental backup should run now.

        Args:
            settings: Current DataSecuritySettings

        Returns:
            (should_run: bool, reason: str, scheduled_time_ms: int | None)
        """
        # Check if backup is already running
        if self._has_running_backup():
            return False, "已有备份任务正在运行", None

        # Only run if incremental schedule is configured
        if not settings.incremental_schedule:
            return False, "增量备份时间未设置", None

        now = datetime.now()
        scheduled_ms = self._latest_scheduled_time_ms(settings.incremental_schedule, now)
        if scheduled_ms is None:
            return False, "增量 cron 无效或当前未到触发点", None

        last_success_ms = settings.last_incremental_backup_time_ms or 0
        last_marker_ms = max(last_success_ms, self._last_incremental_attempt_ms or 0)
        if scheduled_ms <= last_marker_ms:
            return False, "增量备份已在本次调度窗口尝试/完成", scheduled_ms

        return True, f"到达增量备份计划时间（{settings.incremental_schedule}）", scheduled_ms

    def _should_run_full_backup(self, settings) -> tuple[bool, str, int | None]:
        """
        Check if full backup should run now.

        Args:
            settings: Current DataSecuritySettings

        Returns:
            (should_run: bool, reason: str, scheduled_time_ms: int | None)
        """
        # Check if backup is already running
        if self._has_running_backup():
            return False, "已有备份任务正在运行", None

        if not getattr(settings, "full_backup_enabled", False):
            return False, "全量备份未启用", None

        # Only run if full backup schedule is configured
        if not settings.full_backup_schedule:
            return False, "全量备份时间未设置", None

        now = datetime.now()
        scheduled_ms = self._latest_scheduled_time_ms(settings.full_backup_schedule, now)
        if scheduled_ms is None:
            return False, "全量 cron 无效或当前未到触发点", None

        last_success_ms = settings.last_full_backup_time_ms or 0
        last_marker_ms = max(last_success_ms, self._last_full_attempt_ms or 0)
        if scheduled_ms <= last_marker_ms:
            return False, "全量备份已在本次调度窗口尝试/完成", scheduled_ms

        return True, f"到达全量备份计划时间（{settings.full_backup_schedule}）", scheduled_ms

    def _run_incremental_backup(self, scheduled_ms: int | None):
        """Run incremental backup (fire-and-forget)."""
        try:
            job_id = start_job_if_idle(reason="定时增量备份", full_backup=False)
            logger.info(f"Started incremental backup job #{job_id}")
            self.store.touch_last_run(int(time.time() * 1000))
            if scheduled_ms is not None:
                self._last_incremental_attempt_ms = int(scheduled_ms)

        except Exception as e:
            logger.error(f"Failed to run incremental backup: {e}", exc_info=True)

    def _run_full_backup(self, scheduled_ms: int | None):
        """Run full backup (fire-and-forget)."""
        try:
            job_id = start_job_if_idle(reason="定时全量备份", full_backup=True)
            logger.info(f"Started full backup job #{job_id}")
            self.store.touch_last_run(int(time.time() * 1000))
            if scheduled_ms is not None:
                self._last_full_attempt_ms = int(scheduled_ms)

        except Exception as e:
            logger.error(f"Failed to run full backup: {e}", exc_info=True)

    def _scheduler_loop(self):
        """Main scheduler loop - runs every 60 seconds"""
        logger.info("Backup scheduler V2 started")

        try:
            while not self._stop_event.is_set():
                try:
                    # Get current settings
                    settings = self.store.get_settings()

                    # Check if scheduled backups are enabled
                    if not settings.enabled:
                        logger.debug("Backups disabled, waiting 60s")
                        self._stop_event.wait(60)
                        continue

                    inc_should_run, inc_reason, inc_scheduled_ms = self._should_run_incremental_backup(settings)
                    full_should_run, full_reason, full_scheduled_ms = self._should_run_full_backup(settings)

                    # If both are due in the same window, prefer full backup and skip incremental for this tick.
                    if full_should_run:
                        logger.info(f"Running full backup: {full_reason}")
                        self._run_full_backup(full_scheduled_ms)
                    elif inc_should_run:
                        logger.info(f"Running incremental backup: {inc_reason}")
                        self._run_incremental_backup(inc_scheduled_ms)

                    # Wait 60 seconds before next check
                    self._stop_event.wait(60)

                except Exception as e:
                    logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                    # Continue running despite errors
                    self._stop_event.wait(60)

        except Exception as e:
            logger.error(f"Fatal error in scheduler: {e}", exc_info=True)

        logger.info("Backup scheduler V2 stopped")

    def start(self):
        """Start the scheduler in background"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Backup scheduler V2 started")

    def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Backup scheduler V2 stopped")

    @property
    def is_running(self) -> bool:
        return self._running


# Global scheduler instance
_scheduler_v2: BackupSchedulerV2 | None = None


def get_scheduler_v2() -> BackupSchedulerV2 | None:
    """Get the global scheduler instance"""
    return _scheduler_v2


def init_scheduler_v2(store: DataSecurityStore) -> BackupSchedulerV2:
    """
    Initialize the global scheduler instance.

    Args:
        store: DataSecurityStore instance

    Returns:
        The scheduler instance (not started yet)
    """
    global _scheduler_v2
    _scheduler_v2 = BackupSchedulerV2(store)
    return _scheduler_v2


def start_scheduler_v2():
    """Start the global scheduler"""
    if _scheduler_v2:
        _scheduler_v2.start()


def stop_scheduler_v2():
    """Stop the global scheduler"""
    if _scheduler_v2:
        _scheduler_v2.stop()
