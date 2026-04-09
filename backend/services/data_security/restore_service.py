from __future__ import annotations

from dataclasses import dataclass
import hashlib
import sqlite3
import shutil
import time
from pathlib import Path

from backend.app.core.paths import repo_root
from backend.database.paths import resolve_auth_db_path

from .backup_service import _compute_backup_package_hash
from .sqlite_backup import sqlite_online_backup
from .store import DataSecurityStore


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _sqlite_content_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    conn = sqlite3.connect(str(path))
    try:
        for line in conn.iterdump():
            hasher.update(line.encode("utf-8"))
            hasher.update(b"\n")
    finally:
        conn.close()
    return hasher.hexdigest()


def _sanitize_target_name(value: str) -> str:
    text = "".join(ch for ch in str(value or "").strip() if ch.isalnum() or ch in ("-", "_"))
    return text or "restore_target"


REAL_RESTORE_CONFIRMATION_TEXT = "RESTORE"


@dataclass(frozen=True)
class RealRestoreExecutionResult:
    job_id: int
    backup_path: str
    backup_hash: str
    actual_backup_hash: str
    hash_match: bool
    compare_match: bool
    source_auth_db_path: str
    source_auth_db_hash: str
    live_auth_db_path: str
    live_auth_db_hash: str
    executed_by: str
    executed_at_ms: int
    change_reason: str
    result: str
    notes: str

    def as_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "backup_path": self.backup_path,
            "backup_hash": self.backup_hash,
            "actual_backup_hash": self.actual_backup_hash,
            "hash_match": self.hash_match,
            "compare_match": self.compare_match,
            "source_auth_db_path": self.source_auth_db_path,
            "source_auth_db_hash": self.source_auth_db_hash,
            "live_auth_db_path": self.live_auth_db_path,
            "live_auth_db_hash": self.live_auth_db_hash,
            "executed_by": self.executed_by,
            "executed_at_ms": self.executed_at_ms,
            "change_reason": self.change_reason,
            "result": self.result,
            "notes": self.notes,
        }


class RestoreDrillExecutionService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def execute_drill(
        self,
        *,
        job_id: int,
        backup_path: str,
        backup_hash: str,
        restore_target: str,
        executed_by: str,
        executed_at_ms: int | None = None,
        verification_notes: str | None = None,
    ):
        job = self.store.get_job(int(job_id))
        local_backup_path = str(job.output_dir or "").strip()
        job_package_hash = str(job.package_hash or "").strip()
        provided_backup_path = str(backup_path or "").strip()
        provided_backup_hash = str(backup_hash or "").strip()

        if not local_backup_path:
            raise ValueError("restore_drill_requires_local_backup")
        if not job_package_hash:
            raise ValueError("restore_drill_requires_job_package_hash")
        if provided_backup_path != local_backup_path:
            raise ValueError("restore_drill_backup_path_must_match_local_backup")
        if provided_backup_hash != job_package_hash:
            raise ValueError("restore_drill_backup_hash_must_match_job_package_hash")

        pack_dir = Path(provided_backup_path)
        expected_hash = provided_backup_hash
        when_ms = int(time.time() * 1000) if executed_at_ms is None else int(executed_at_ms)
        report: dict[str, object] = {
            "job_id": int(job.id),
            "job_status": str(job.status),
            "job_package_hash": (str(job.package_hash) if job.package_hash else None),
            "provided_backup_hash": expected_hash,
            "backup_path": str(pack_dir),
            "checks": [],
        }

        actual_backup_hash: str | None = None
        restored_auth_db_path: str | None = None
        restored_auth_db_hash: str | None = None
        hash_match = False
        compare_match = False
        package_validation_status = "passed"
        acceptance_status = "passed"
        result = "success"
        notes: list[str] = []

        if not pack_dir.exists() or not pack_dir.is_dir():
            package_validation_status = "blocked"
            acceptance_status = "blocked"
            result = "failed"
            notes.append("backup package path does not exist or is not a directory")
            report["checks"].append({"name": "package_exists", "status": "failed"})
        else:
            report["checks"].append({"name": "package_exists", "status": "passed"})

        if expected_hash and job.package_hash and expected_hash != str(job.package_hash):
            package_validation_status = "blocked"
            acceptance_status = "blocked"
            result = "failed"
            notes.append("provided backup hash does not match job package hash")
            report["checks"].append({"name": "provided_hash_matches_job", "status": "failed"})
        else:
            report["checks"].append({"name": "provided_hash_matches_job", "status": "passed"})

        if package_validation_status == "passed":
            actual_backup_hash = _compute_backup_package_hash(pack_dir)
            hash_match = actual_backup_hash == expected_hash
            report["actual_backup_hash"] = actual_backup_hash
            report["checks"].append(
                {
                    "name": "package_hash_match",
                    "status": "passed" if hash_match else "failed",
                    "expected": expected_hash,
                    "actual": actual_backup_hash,
                }
            )
            if not hash_match:
                package_validation_status = "blocked"
                acceptance_status = "blocked"
                result = "failed"
                notes.append("backup package hash mismatch; restore verification blocked")

        source_auth_db = pack_dir / "auth.db"
        backup_settings_path = pack_dir / "backup_settings.json"
        if package_validation_status == "passed":
            if not source_auth_db.exists():
                package_validation_status = "failed"
                acceptance_status = "failed"
                result = "failed"
                notes.append("auth.db missing from backup package")
                report["checks"].append({"name": "auth_db_present", "status": "failed"})
            else:
                report["checks"].append({"name": "auth_db_present", "status": "passed"})
            if not backup_settings_path.exists():
                package_validation_status = "failed"
                acceptance_status = "failed"
                result = "failed"
                notes.append("backup_settings.json missing from backup package")
                report["checks"].append({"name": "backup_settings_present", "status": "failed"})
            else:
                report["checks"].append({"name": "backup_settings_present", "status": "passed"})

        if package_validation_status == "passed":
            restore_root = repo_root() / "data" / "restore_drills" / _sanitize_target_name(restore_target)
            restore_root.mkdir(parents=True, exist_ok=True)
            restored_dir = restore_root / f"job_{int(job_id)}_{when_ms}"
            restored_dir.mkdir(parents=True, exist_ok=True)
            restored_auth_db = restored_dir / "auth.db"
            shutil.copy2(source_auth_db, restored_auth_db)
            restored_auth_db_path = str(restored_auth_db)

            source_hash = _file_sha256(source_auth_db)
            restored_auth_db_hash = _file_sha256(restored_auth_db)
            compare_match = source_hash == restored_auth_db_hash
            report["checks"].append(
                {
                    "name": "restored_auth_db_compare",
                    "status": "passed" if compare_match else "failed",
                    "source_hash": source_hash,
                    "restored_hash": restored_auth_db_hash,
                    "restored_auth_db_path": restored_auth_db_path,
                }
            )
            if not compare_match:
                acceptance_status = "failed"
                result = "failed"
                notes.append("restored auth.db hash mismatch after system copy verification")

        system_summary = "; ".join(notes) if notes else "restore drill verification passed"
        if verification_notes:
            system_summary = f"{system_summary}; operator_notes={verification_notes}"
        report["package_validation_status"] = package_validation_status
        report["acceptance_status"] = acceptance_status
        report["result"] = result

        return self.store.create_restore_drill(
            job_id=int(job_id),
            backup_path=str(pack_dir),
            backup_hash=expected_hash,
            actual_backup_hash=actual_backup_hash,
            hash_match=hash_match,
            restore_target=str(restore_target),
            restored_auth_db_path=restored_auth_db_path,
            restored_auth_db_hash=restored_auth_db_hash,
            compare_match=compare_match,
            package_validation_status=package_validation_status,
            acceptance_status=acceptance_status,
            executed_by=str(executed_by),
            executed_at_ms=when_ms,
            result=result,
            verification_notes=system_summary,
            verification_report=report,
        )


class RealRestoreExecutionService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def execute_restore(
        self,
        *,
        job_id: int,
        backup_path: str,
        backup_hash: str,
        change_reason: str,
        confirmation_text: str,
        executed_by: str,
        executed_at_ms: int | None = None,
    ) -> RealRestoreExecutionResult:
        job = self.store.get_job(int(job_id))
        local_backup_path = str(job.output_dir or "").strip()
        job_package_hash = str(job.package_hash or "").strip()
        provided_backup_path = str(backup_path or "").strip()
        provided_backup_hash = str(backup_hash or "").strip()
        normalized_reason = str(change_reason or "").strip()
        normalized_confirmation = str(confirmation_text or "").strip()
        normalized_actor = str(executed_by or "").strip()

        if not normalized_reason:
            raise ValueError("change_reason_required")
        if not normalized_confirmation:
            raise ValueError("restore_confirmation_text_required")
        if normalized_confirmation != REAL_RESTORE_CONFIRMATION_TEXT:
            raise ValueError("restore_confirmation_text_invalid")
        if not normalized_actor:
            raise ValueError("executed_by_required")
        active_job_id = self.store.get_active_job_id()
        if active_job_id is not None:
            raise RuntimeError(f"restore_requires_no_active_backup_job:{active_job_id}")
        if not local_backup_path:
            raise ValueError("restore_requires_local_backup")
        if not job_package_hash:
            raise ValueError("restore_requires_job_package_hash")
        if provided_backup_path != local_backup_path:
            raise ValueError("restore_backup_path_must_match_local_backup")
        if provided_backup_hash != job_package_hash:
            raise ValueError("restore_backup_hash_must_match_job_package_hash")

        pack_dir = Path(provided_backup_path)
        if not pack_dir.exists() or not pack_dir.is_dir():
            raise ValueError("restore_backup_package_not_found")

        actual_backup_hash = _compute_backup_package_hash(pack_dir)
        if actual_backup_hash != provided_backup_hash:
            raise ValueError("restore_backup_hash_mismatch")

        source_auth_db = pack_dir / "auth.db"
        if not source_auth_db.exists():
            raise ValueError("restore_auth_db_missing")
        backup_settings_path = pack_dir / "backup_settings.json"
        if not backup_settings_path.exists():
            raise ValueError("restore_backup_settings_missing")

        live_auth_db = resolve_auth_db_path(self.store.get_settings().auth_db_path)
        if not live_auth_db.exists():
            raise RuntimeError(f"restore_live_auth_db_not_found:{live_auth_db}")

        try:
            sqlite_online_backup(source_auth_db, live_auth_db)
        except Exception as exc:
            raise RuntimeError(f"restore_live_auth_db_copy_failed:{exc}") from exc

        source_hash = _sqlite_content_sha256(source_auth_db)
        live_hash = _sqlite_content_sha256(live_auth_db)
        compare_match = source_hash == live_hash
        if not compare_match:
            raise RuntimeError("restore_live_auth_db_hash_mismatch")

        when_ms = int(time.time() * 1000) if executed_at_ms is None else int(executed_at_ms)
        return RealRestoreExecutionResult(
            job_id=int(job.id),
            backup_path=str(pack_dir),
            backup_hash=provided_backup_hash,
            actual_backup_hash=actual_backup_hash,
            hash_match=True,
            compare_match=True,
            source_auth_db_path=str(source_auth_db),
            source_auth_db_hash=source_hash,
            live_auth_db_path=str(live_auth_db),
            live_auth_db_hash=live_hash,
            executed_by=normalized_actor,
            executed_at_ms=when_ms,
            change_reason=normalized_reason,
            result="success",
            notes="live auth.db restored from selected local backup package and sqlite content matched source backup",
        )
