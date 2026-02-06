from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path

from backend.app.core.paths import repo_root
from backend.services.data_security_store import DataSecurityStore

from .common import ensure_dir, timestamp, run_cmd
from .backup_steps import (
    BackupContext,
    BackupCancelledError,
    backup_precheck_and_prepare,
    backup_sqlite_db,
    backup_ragflow_volumes,
    backup_docker_images,
    write_backup_settings_snapshot,
)
from .docker_utils import (
    docker_ok,
)


# Keep a compatibility helper for older modules that import `_run` from `data_security_backup`.
def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    return run_cmd(cmd, cwd=cwd)


def _list_migration_packs(target_dir: Path) -> list[Path]:
    """
    List `migration_pack_*` directories under target_dir, oldest-first.

    Sorting uses mtime as a best-effort proxy for creation time. We deliberately avoid parsing
    timestamps from names because older backups may include different suffixes.
    """
    try:
        items = [p for p in target_dir.iterdir() if p.is_dir() and p.name.startswith("migration_pack_")]
    except Exception:
        return []

    def _mtime(p: Path) -> float:
        try:
            return float(p.stat().st_mtime)
        except Exception:
            return 0.0

    return sorted(items, key=_mtime)


def _prune_old_backup_packs(*, target_dir: Path, keep_max: int, keep_dir: Path) -> list[Path]:
    """
    Prune old migration packs under `target_dir`, keeping at most `keep_max` directories.

    Never deletes `keep_dir`. Returns deleted directories.
    """
    keep_max = int(keep_max)
    if keep_max <= 0:
        return []

    packs = _list_migration_packs(target_dir)
    if not packs:
        return []

    deleted: list[Path] = []
    # Exclude the current pack from deletion candidates.
    candidates = [p for p in packs if p.resolve() != keep_dir.resolve()]
    # If we have more packs than keep_max, delete the oldest ones.
    excess = max(0, len(packs) - keep_max)
    for p in candidates[:excess]:
        try:
            shutil.rmtree(p)
            deleted.append(p)
        except Exception:
            # Best-effort: pruning must never fail the backup job.
            continue
    return deleted


class DataSecurityBackupService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def run_job(self, job_id: int, *, include_images: bool | None = None) -> None:
        job_kind: str | None = None
        try:
            job_kind = self.store.get_job(job_id).kind
        except Exception:
            job_kind = None

        settings = self.store.get_settings()
        if include_images is None:
            include_images = bool(getattr(settings, "full_backup_include_images", 1))

        now_ms = int(time.time() * 1000)
        self.store.update_job(job_id, status="running", progress=1, message="开始备份", started_at_ms=now_ms)

        ctx = BackupContext(store=self.store, job_id=job_id, settings=settings, include_images=bool(include_images), job_kind=job_kind)
        # Keep legacy sanity: docker_ok is still checked here too, because some callers import it.
        ok, why = docker_ok()
        if not ok:
            raise RuntimeError(f"Docker 不可用：{why}")

        try:
            backup_precheck_and_prepare(ctx)
            backup_sqlite_db(ctx)
            backup_ragflow_volumes(ctx)
            backup_docker_images(ctx)
            write_backup_settings_snapshot(ctx)
        except BackupCancelledError:
            try:
                self.store.mark_job_canceled(job_id, message="已取消", detail="user_requested")
            except Exception:
                pass
            return

        if not ctx.pack_dir:
            raise RuntimeError("pack_dir not prepared")
        pack_dir = ctx.pack_dir

        # Retention: prune older backup packs under the same target directory.
        # This keeps the backup directory bounded without changing where backups are written.
        try:
            keep_max = int(getattr(settings, "backup_retention_max", 30) or 30)
            keep_max = max(1, min(100, keep_max))
            deleted = _prune_old_backup_packs(target_dir=pack_dir.parent, keep_max=keep_max, keep_dir=pack_dir)
            if deleted:
                logging.getLogger(__name__).info(
                    "[Backup] pruned old packs: keep_max=%s deleted=%s target=%s",
                    keep_max,
                    len(deleted),
                    str(pack_dir.parent),
                )
        except Exception as e:
            logging.getLogger(__name__).warning("[Backup] retention prune skipped: %s", e, exc_info=True)

        backup_done_ms = int(time.time() * 1000)
        # Keep job running while we perform post-backup steps (replication).
        self.store.update_job(job_id, status="running", progress=90, message="备份完成，准备同步")
        try:
            if job_kind == "full":
                self.store.update_last_full_backup_time(backup_done_ms)
            elif job_kind == "incremental":
                self.store.update_last_incremental_backup_time(backup_done_ms)
        except Exception:
            # Best-effort: backup succeeded; scheduling metadata must not fail the job.
            pass

        # Automatic replication to mounted SMB share
        replicated = False
        try:
            from .replica_service import BackupReplicaService
            replica_svc = BackupReplicaService(self.store)
            replicated = bool(replica_svc.replicate_backup(pack_dir, job_id))
        except Exception as e:
            # Replication failure should not mark the backup as failed
            logger = logging.getLogger(__name__)
            logger.error(f"Replication failed: {e}", exc_info=True)
            # Update message to indicate replication failure, but keep status as "completed"
            try:
                self.store.update_job(
                    job_id,
                    message=f"备份完成（同步失败：{str(e)}）",
                    detail=str(e),
                    progress=100
                )
            except Exception:
                pass
        finally:
            finished_at_ms = int(time.time() * 1000)
            # If replication is disabled, or replication didn't update the progress to 100, finish the job here.
            try:
                if not replicated:
                    # Keep any error message written by replica service; only set a default if still at the pre-sync message.
                    try:
                        current = self.store.get_job(job_id)
                        if (current.message or "") == "备份完成，准备同步":
                            self.store.update_job(job_id, message="备份完成")
                    except Exception:
                        pass
                self.store.update_job(job_id, status="completed", progress=100, finished_at_ms=finished_at_ms)
            except Exception:
                pass

    def run_incremental_backup_job(self, job_id: int) -> None:
        """
        Incremental backup:
        - Excludes Docker images to keep runtime/size manageable.
        """
        self.run_job(job_id, include_images=False)

    def run_full_backup_job(self, job_id: int) -> None:
        """
        Full backup:
        - Respects `full_backup_include_images` in settings.
        """
        settings = self.store.get_settings()
        self.run_job(job_id, include_images=bool(getattr(settings, "full_backup_include_images", 1)))
