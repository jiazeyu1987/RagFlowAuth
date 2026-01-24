"""
Backup scheduler with cron-like functionality.
Runs scheduled backups based on cron expressions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from backend.services.data_security_store import DataSecurityStore


logger = logging.getLogger(__name__)


def _should_run_now(schedule: str, last_check_time: float) -> bool:
    """
    Check if a scheduled backup should run now based on cron expression.

    Cron format: "minute hour day month weekday"
    Example: "0 2 * * *" = daily at 2:00 AM
             "0 4 * * 1" = weekly on Monday at 4:00 AM

    Args:
        schedule: Cron expression (5 parts)
        last_check_time: Unix timestamp of last check

    Returns:
        True if the scheduled time has been reached since last check
    """
    try:
        parts = schedule.strip().split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron format: {schedule}")
            return False

        minute, hour, day, month, weekday = parts

        # Get current time
        now = time.time()
        current_dt = datetime.fromtimestamp(now)
        last_dt = datetime.fromtimestamp(last_check_time)

        # Check if current time matches schedule
        # For simplicity, we check if we're in a different minute/hour/day
        # and the current time matches the cron expression

        # Parse cron parts
        target_minute = int(minute) if minute != "*" else None
        target_hour = int(hour) if hour != "*" else None
        target_day = int(day) if day != "*" else None
        target_month = int(month) if month != "*" else None
        target_weekday = int(weekday) if weekday != "*" else None

        # Check if we've passed a scheduled time
        # Simple approach: check every minute if we match the schedule
        # and if we're in a new time period since last check

        # Get the most recent time that matched the schedule
        candidates = []

        # Check last hour
        for h in range(24):
            if target_hour is not None and h != target_hour:
                continue
            for m in range(60):
                if target_minute is not None and m != target_minute:
                    continue

                check_dt = current_dt.replace(hour=h, minute=m, second=0, microsecond=0)

                # Check day/month/weekday constraints
                if target_day is not None and check_dt.day != target_day:
                    continue
                if target_month is not None and check_dt.month != target_month:
                    continue
                if target_weekday is not None and check_dt.weekday() != target_weekday:
                    continue

                candidates.append(check_dt.timestamp())

        if not candidates:
            return False

        # Get the most recent scheduled time
        last_scheduled = max(candidates)

        # Return True if the scheduled time has passed since last check
        return last_scheduled > last_check_time and last_scheduled <= now

    except Exception as e:
        logger.error(f"Error checking schedule '{schedule}': {e}")
        return False


class BackupScheduler:
    """
    Background scheduler for automated backups.
    Checks every minute if scheduled backups should run.
    """

    def __init__(self, store: DataSecurityStore, backup_service):
        """
        Args:
            store: DataSecurityStore instance
            backup_service: DataSecurityService instance with run_backup/ run_full_backup methods
        """
        self.store = store
        self.backup_service = backup_service
        self._running = False
        self._task = None
        self._last_check_time = time.time()

    async def _scheduler_loop(self):
        """Main scheduler loop - runs every minute"""
        logger.info("Backup scheduler started")

        while self._running:
            try:
                # Get current settings
                settings = self.store.get_settings()

                # Check if scheduled backups are enabled
                if not settings.enabled:
                    await asyncio.sleep(60)
                    continue

                # Check incremental backup schedule
                if settings.incremental_schedule:
                    if _should_run_now(settings.incremental_schedule, self._last_check_time):
                        logger.info(f"Running scheduled incremental backup (schedule: {settings.incremental_schedule})")
                        try:
                            await self._run_incremental_backup()
                        except Exception as e:
                            logger.error(f"Scheduled incremental backup failed: {e}")

                # Check full backup schedule
                if settings.full_backup_enabled and settings.full_backup_schedule:
                    if _should_run_now(settings.full_backup_schedule, self._last_check_time):
                        logger.info(f"Running scheduled full backup (schedule: {settings.full_backup_schedule})")
                        try:
                            await self._run_full_backup()
                        except Exception as e:
                            logger.error(f"Scheduled full backup failed: {e}")

                # Update last check time
                self._last_check_time = time.time()

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            # Wait 60 seconds before next check
            await asyncio.sleep(60)

        logger.info("Backup scheduler stopped")

    async def _run_incremental_backup(self):
        """Run incremental backup"""
        # Create job and run
        job = self.store.create_job(status="queued", message="定时增量备份")
        await asyncio.to_thread(
            self.backup_service.run_backup,
            job.id,
            reason="定时增量备份"
        )

    async def _run_full_backup(self):
        """Run full backup"""
        # Create job and run
        job = self.store.create_job(status="queued", message="定时全量备份")
        await asyncio.to_thread(
            self.backup_service.run_full_backup,
            job.id,
            reason="定时全量备份"
        )

    def start(self):
        """Start the scheduler in background"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Backup scheduler scheduled to start")

    def stop(self):
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Backup scheduler stop requested")

    @property
    def is_running(self) -> bool:
        return self._running


# Global scheduler instance
_scheduler: BackupScheduler | None = None


def get_scheduler() -> BackupScheduler | None:
    """Get the global scheduler instance"""
    return _scheduler


def init_scheduler(store: DataSecurityStore, backup_service) -> BackupScheduler:
    """
    Initialize the global scheduler instance.

    Args:
        store: DataSecurityStore instance
        backup_service: DataSecurityService instance

    Returns:
        The scheduler instance (not started yet)
    """
    global _scheduler
    _scheduler = BackupScheduler(store, backup_service)
    return _scheduler


def start_scheduler():
    """Start the global scheduler"""
    if _scheduler:
        _scheduler.start()


def stop_scheduler():
    """Stop the global scheduler"""
    if _scheduler:
        _scheduler.stop()
