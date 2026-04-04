from __future__ import annotations

import hashlib
import logging
import shutil
import time
from pathlib import Path

from backend.services.data_security_store import DataSecurityStore

from .backup_steps import (
    BackupCancelledError,
    BackupContext,
    backup_docker_images,
    backup_precheck_and_prepare,
    backup_ragflow_volumes,
    backup_sqlite_db,
    write_backup_settings_snapshot,
)
from .common import run_cmd
from .docker_utils import docker_ok


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    return run_cmd(cmd, cwd=cwd)


def _list_migration_packs(target_dir: Path) -> list[Path]:
    try:
        items = [p for p in target_dir.iterdir() if p.is_dir() and p.name.startswith("migration_pack_")]
    except Exception:
        return []

    def _mtime(path: Path) -> float:
        try:
            return float(path.stat().st_mtime)
        except Exception:
            return 0.0

    return sorted(items, key=_mtime)


def _prune_old_backup_packs(*, target_dir: Path, keep_max: int, keep_dir: Path) -> list[Path]:
    keep_max = int(keep_max)
    if keep_max <= 0:
        return []

    packs = _list_migration_packs(target_dir)
    if not packs:
        return []

    deleted: list[Path] = []
    candidates = [p for p in packs if p.resolve() != keep_dir.resolve()]
    excess = max(0, len(packs) - keep_max)
    for path in candidates[:excess]:
        try:
            shutil.rmtree(path)
            deleted.append(path)
        except Exception:
            continue
    return deleted


def _cleanup_empty_parents(path: Path, *, stop_at: Path) -> None:
    current = path
    try:
        stop_real = stop_at.resolve()
    except Exception:
        stop_real = stop_at

    while True:
        try:
            current_real = current.resolve()
        except Exception:
            current_real = current
        if current_real == stop_real:
            break
        try:
            current.rmdir()
        except Exception:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent


def _finalize_local_backup(*, pack_dir: Path, local_root: Path) -> Path:
    local_root.mkdir(parents=True, exist_ok=True)
    final_dir = local_root / pack_dir.name
    if final_dir.exists():
        raise RuntimeError(f"local_backup_destination_exists:{final_dir}")
    pack_dir.rename(final_dir)
    _cleanup_empty_parents(pack_dir.parent, stop_at=local_root / "_staging")
    return final_dir


def _compute_backup_package_hash(pack_dir: Path) -> str:
    if not pack_dir.exists() or not pack_dir.is_dir():
        raise RuntimeError(f"backup_package_not_found: {pack_dir}")

    hasher = hashlib.sha256()
    for path in sorted(pack_dir.rglob("*"), key=lambda item: item.relative_to(pack_dir).as_posix()):
        rel = path.relative_to(pack_dir).as_posix()
        if path.is_dir():
            hasher.update(f"D:{rel}\n".encode("utf-8"))
            continue
        if not path.is_file():
            continue
        hasher.update(f"F:{rel}\n".encode("utf-8"))
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
    return hasher.hexdigest()


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
        self.store.update_job(
            job_id,
            status="running",
            progress=1,
            message="backup_started",
            started_at_ms=now_ms,
            replication_status=("pending" if bool(getattr(settings, "replica_enabled", False)) else "skipped"),
            verification_status="not_verified",
        )

        ctx = BackupContext(
            store=self.store,
            job_id=job_id,
            settings=settings,
            include_images=bool(include_images),
            job_kind=job_kind,
        )
        ok, why = docker_ok()
        if not ok:
            raise RuntimeError(f"docker_unavailable:{why}")

        try:
            backup_precheck_and_prepare(ctx)
            backup_sqlite_db(ctx)
            backup_ragflow_volumes(ctx)
            backup_docker_images(ctx)
            write_backup_settings_snapshot(ctx)
        except BackupCancelledError:
            try:
                self.store.mark_job_canceled(job_id, message="backup_canceled", detail="user_requested")
            except Exception:
                pass
            return

        if not ctx.pack_dir:
            raise RuntimeError("pack_dir_not_prepared")
        staged_pack_dir = ctx.pack_dir
        local_root = Path(settings.local_backup_target_path())

        self.store.update_job(job_id, status="running", progress=88, message="backup_hashing")
        package_hash = _compute_backup_package_hash(staged_pack_dir)
        self.store.update_job(job_id, package_hash=package_hash)

        keep_max = int(getattr(settings, "backup_retention_max", 30) or 30)
        keep_max = max(1, min(100, keep_max))

        local_output_dir: Path | None = None
        local_error: str | None = None
        source_pack_dir = staged_pack_dir

        self.store.update_job(job_id, status="running", progress=90, message="backup_localizing")
        try:
            local_output_dir = _finalize_local_backup(pack_dir=staged_pack_dir, local_root=local_root)
            source_pack_dir = local_output_dir
            self.store.update_job(
                job_id,
                output_dir=str(local_output_dir),
                progress=92,
                message="backup_local_completed",
            )
            try:
                _prune_old_backup_packs(target_dir=local_root, keep_max=keep_max, keep_dir=local_output_dir)
            except Exception as exc:
                logging.getLogger(__name__).warning("[Backup] local retention prune skipped: %s", exc, exc_info=True)
        except Exception as exc:
            local_error = str(exc)
            self.store.update_job(
                job_id,
                output_dir="",
                progress=92,
                message="backup_local_failed",
                detail=local_error,
            )

        backup_done_ms = int(time.time() * 1000)
        self.store.update_job(
            job_id,
            status="running",
            progress=94,
            message="backup_completed_waiting_windows",
        )
        try:
            if job_kind == "full":
                self.store.update_last_full_backup_time(backup_done_ms)
            elif job_kind == "incremental":
                self.store.update_last_incremental_backup_time(backup_done_ms)
        except Exception:
            pass

        replicated = False
        replication_error: str | None = None
        try:
            from .replica_service import BackupReplicaService

            replicated = bool(BackupReplicaService(self.store).replicate_backup(source_pack_dir, job_id))
            if replicated:
                current_job = self.store.get_job(job_id)
                if current_job.replica_path:
                    try:
                        _prune_old_backup_packs(
                            target_dir=Path(current_job.replica_path).parent,
                            keep_max=keep_max,
                            keep_dir=Path(current_job.replica_path),
                        )
                    except Exception as exc:
                        logging.getLogger(__name__).warning(
                            "[Backup] windows retention prune skipped: %s",
                            exc,
                            exc_info=True,
                        )
        except Exception as exc:
            logging.getLogger(__name__).error("Replication failed: %s", exc, exc_info=True)
            replication_error = str(exc)

        finished_at_ms = int(time.time() * 1000)
        current_job = self.store.get_job(job_id)
        local_succeeded = bool(current_job.output_dir)
        current_replication_status = str(current_job.replication_status or "").strip()
        if current_replication_status in ("", "pending"):
            if replicated:
                final_replication_status = "succeeded"
            elif replication_error or bool(getattr(settings, "replica_enabled", False)):
                final_replication_status = "failed"
            else:
                final_replication_status = "skipped"
        else:
            final_replication_status = current_replication_status
        final_replication_error = replication_error or current_job.replication_error
        if final_replication_status == "failed" and not final_replication_error:
            final_replication_error = "windows_backup_failed"
        if final_replication_status == "skipped" and not final_replication_error:
            final_replication_error = "windows_backup_skipped"
        windows_succeeded = final_replication_status == "succeeded" and bool(current_job.replica_path)

        final_detail_parts: list[str] = []
        if local_error:
            final_detail_parts.append(f"local_backup_failed:{local_error}")
        if final_replication_status == "failed" and final_replication_error:
            final_detail_parts.append(f"windows_backup_failed:{final_replication_error}")
        elif final_replication_status == "skipped" and final_replication_error:
            final_detail_parts.append(f"windows_backup_skipped:{final_replication_error}")

        if local_succeeded and windows_succeeded:
            final_status = "completed"
            final_message = "backup_completed_local_and_windows"
        elif local_succeeded:
            final_status = "completed"
            final_message = "backup_completed_local_only"
        elif windows_succeeded:
            final_status = "completed"
            final_message = "backup_completed_windows_only"
        else:
            final_status = "failed"
            final_message = "backup_failed_local_and_windows"

        final_detail = "; ".join(part for part in final_detail_parts if part) or None
        self.store.update_job(
            job_id,
            status=final_status,
            progress=100,
            message=final_message,
            detail=final_detail,
            replication_status=final_replication_status,
            replication_error=(final_replication_error if final_replication_status in ("failed", "skipped") else None),
            finished_at_ms=finished_at_ms,
        )

    def run_incremental_backup_job(self, job_id: int) -> None:
        self.run_job(job_id, include_images=False)

    def run_full_backup_job(self, job_id: int) -> None:
        settings = self.store.get_settings()
        self.run_job(job_id, include_images=bool(getattr(settings, "full_backup_include_images", 1)))
