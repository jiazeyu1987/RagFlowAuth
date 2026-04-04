from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .common import ensure_dir, run_cmd
from .docker_utils import container_path_to_host_str
from .store import DataSecurityStore

logger = logging.getLogger(__name__)


class BackupReplicaService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def replicate_backup(self, pack_dir: Path, job_id: int) -> bool:
        logger.info("[REPLICATION START] Job ID: %s, Pack: %s", job_id, pack_dir.name)
        settings = self.store.get_settings()

        if not getattr(settings, "replica_enabled", False):
            self.store.update_job(
                job_id,
                message="backup_windows_skipped",
                progress=97,
                replication_status="skipped",
                replication_error="replica_disabled",
            )
            return False

        target_path = str(settings.windows_target_path() or "").strip()
        if not target_path:
            self.store.update_job(
                job_id,
                message="backup_windows_skipped",
                progress=97,
                replication_status="skipped",
                replication_error="windows_target_not_configured",
            )
            return False

        target_base = Path(target_path)
        if not target_base.is_absolute():
            detail = f"replica_target_path={target_path!r}"
            self.store.update_job(
                job_id,
                message="backup_windows_failed",
                progress=97,
                replication_status="failed",
                replication_error=detail,
            )
            return False

        try:
            pack_real = pack_dir.resolve()
            target_real = target_base.resolve()
            if str(pack_real).replace("\\", "/").startswith(str(target_real).replace("\\", "/").rstrip("/") + "/"):
                self.store.update_job(
                    job_id,
                    message="backup_windows_skipped",
                    progress=97,
                    replication_status="skipped",
                    replica_path=str(pack_dir),
                    replication_error="windows_target_same_as_source",
                )
                return False
        except Exception:
            pass

        if self._requires_cifs_mount(target_base) and not self._check_is_cifs_mount(target_base):
            detail = f"{target_base} is not a mounted CIFS share. Files copied to local disk instead."
            self.store.update_job(
                job_id,
                message="backup_windows_skipped",
                progress=97,
                replication_status="skipped",
                replication_error=detail,
            )
            return False

        try:
            subdir = self._generate_subdir(pack_dir.name, settings.replica_subdir_format)
            target_final_dir = target_base / subdir
            target_tmp_dir = target_base / "_tmp" / f"job_{job_id}_{int(time.time())}"

            self.store.update_job(
                job_id,
                message="backup_windows_copying",
                progress=92,
                replication_status="pending",
            )
            self._copy_directory(pack_dir, target_tmp_dir, job_id)

            images_container = pack_dir / "images.tar"
            images_host_str = container_path_to_host_str(images_container)
            if not images_container.exists() and os.path.exists(images_host_str):
                target_images = target_tmp_dir / "images.tar"
                target_images.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(images_host_str), target_images)

            self._write_replication_manifest(target_tmp_dir, pack_dir.name, job_id)
            (target_tmp_dir / "DONE").touch()

            if target_final_dir.exists():
                shutil.rmtree(target_final_dir)
            target_final_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target_tmp_dir), str(target_final_dir))

            self.store.update_job(job_id, message="backup_windows_verifying", progress=97)
            if not self._verify_replication(target_final_dir):
                detail = f"replication verification failed for {target_final_dir}"
                self.store.update_job(
                    job_id,
                    message="backup_windows_failed",
                    replication_status="failed",
                    replication_error=detail,
                )
                return False

            self.store.update_job(
                job_id,
                message="backup_windows_succeeded",
                progress=98,
                replication_status="succeeded",
                replica_path=str(target_final_dir),
                replication_error="",
            )
            logger.info("[REPLICATION SUCCESS] Job ID: %s Target: %s", job_id, target_final_dir)
            return True
        except Exception as exc:
            logger.error("[REPLICATION FAILED] Job ID: %s Error: %s", job_id, exc, exc_info=True)
            self.store.update_job(
                job_id,
                message="backup_windows_failed",
                progress=98,
                replication_status="failed",
                replication_error=str(exc),
            )
            return False

    def _requires_cifs_mount(self, target_path: Path) -> bool:
        target_norm = target_path.as_posix().rstrip("/")
        return target_norm == "/mnt/replica" or target_norm.startswith("/mnt/replica/")

    def _generate_subdir(self, pack_name: str, format_type: str) -> str:
        if format_type == "date":
            return str(Path(datetime.now().strftime("%Y/%m/%d")) / pack_name)
        return pack_name

    def _convert_to_host_path(self, path: Path) -> Path:
        return Path(container_path_to_host_str(path))

    def _copy_directory(self, src: Path, dst: Path, job_id: int):
        ensure_dir(dst)
        total_files = sum(1 for item in src.rglob("*") if item.is_file())
        copied_files = 0

        for item in src.rglob("*"):
            rel = item.relative_to(src)
            target = dst / rel
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source_path = item
            if not source_path.exists():
                source_path = self._convert_to_host_path(item)
            if source_path.exists():
                shutil.copy2(source_path, target)
                copied_files += 1
                if total_files > 0:
                    progress = 92 + int(5 * copied_files / total_files)
                    self.store.update_job(job_id, progress=progress)

        volumes_host = self._convert_to_host_path(src / "volumes")
        if volumes_host.exists() and not (dst / "volumes").exists():
            for item in volumes_host.rglob("*"):
                if not item.is_file():
                    continue
                rel = item.relative_to(volumes_host)
                target = dst / "volumes" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

        helper_image = "ragflowauth-backend:latest"
        try:
            code, out = run_cmd(["docker", "ps", "--filter", "name=ragflowauth-backend", "--format", "{{.Image}}"])
            if code == 0 and out and out.strip():
                helper_image = out.strip()
        except Exception:
            pass

        volumes_on_host_str = container_path_to_host_str(src / "volumes")
        try:
            dst_volumes = dst / "volumes"
            dst_volumes.mkdir(parents=True, exist_ok=True)
            list_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volumes_on_host_str}:/src:ro",
                helper_image,
                "sh",
                "-c",
                "ls -1 /src/*.tar.gz 2>/dev/null || echo ''",
            ]
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout.strip():
                for filename in [line.strip() for line in result.stdout.splitlines() if line.strip()]:
                    copy_cmd = [
                        "docker",
                        "run",
                        "--rm",
                        "-v",
                        f"{volumes_on_host_str}:/src:ro",
                        "-v",
                        f"{dst}:/dst",
                        helper_image,
                        "sh",
                        "-c",
                        f"cp /src/{Path(filename).name} /dst/volumes/ 2>/dev/null || true",
                    ]
                    subprocess.run(copy_cmd, capture_output=True, timeout=60)
        except Exception as exc:
            logger.warning("[Copy] docker-assisted volume copy skipped: %s", exc)

    def _write_replication_manifest(self, target_dir: Path, pack_name: str, job_id: int):
        manifest = {
            "pack_name": pack_name,
            "replicated_at_ms": int(time.time() * 1000),
            "replicated_at": datetime.now().isoformat(),
            "job_id": job_id,
            "source_hostname": (os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "")),
        }
        manifest_file = target_dir / "replication_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    def _check_is_cifs_mount(self, target_path: Path) -> bool:
        try:
            result = subprocess.run(["mount"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            target_str = target_path.as_posix()
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                mount_point = parts[2]
                fstype = parts[4]
                if "cifs" in fstype.lower() and target_str.startswith(mount_point):
                    return True
            return False
        except Exception:
            return False

    def _verify_replication(self, target_dir: Path) -> bool:
        try:
            if not target_dir.exists():
                return False
            if not (target_dir / "DONE").exists():
                return False
            manifest_file = target_dir / "replication_manifest.json"
            if not manifest_file.exists():
                return False
            auth_db = target_dir / "auth.db"
            if not auth_db.exists():
                return False
            with manifest_file.open("r", encoding="utf-8") as fh:
                json.load(fh)
            return True
        except Exception:
            return False
