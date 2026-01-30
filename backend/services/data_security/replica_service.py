from __future__ import annotations

import os
import shutil
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

from .common import ensure_dir
from .store import DataSecurityStore
from .docker_utils import container_path_to_host_str


class BackupReplicaService:
    """Service to replicate backups to mounted SMB share."""

    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def replicate_backup(self, pack_dir: Path, job_id: int) -> bool:
        """
        Replicate backup directory to replica target.

        Args:
            pack_dir: Local backup directory (e.g., /opt/backups/migration_pack_20250125_183000)
            job_id: Backup job ID (for progress updates)

        Returns:
            True if replication succeeded, False otherwise
        """
        settings = self.store.get_settings()

        # Check if replication is enabled
        if not getattr(settings, 'replica_enabled', False):
            return True  # Not enabled, skip

        target_path = settings.replica_target_path
        if not target_path:
            self.store.update_job(job_id, message="备份完成（同步失败：未配置复制目标路径）", detail="replica_target_path is empty")
            return False

        target_base = Path(target_path)
        if not target_base.is_absolute():
            self.store.update_job(job_id, message="备份完成（同步失败：复制目标路径必须是绝对路径）", detail=f"replica_target_path={target_path!r}")
            return False

        try:
            # Generate subdirectory based on format
            subdir = self._generate_subdir(pack_dir.name, settings.replica_subdir_format)
            target_final_dir = target_base / subdir
            target_tmp_dir = target_base / "_tmp" / f"job_{job_id}_{int(time.time())}"

            # Step 1: Copy to temporary directory
            self.store.update_job(job_id, message="开始复制（临时目录）", progress=92)
            self._copy_directory(pack_dir, target_tmp_dir, job_id)

            # Step 1.5: Check and copy images.tar from host path (special handling)
            import os
            images_container = pack_dir / "images.tar"
            images_host_str = container_path_to_host_str(images_container)
            if os.path.exists(images_host_str) and not images_container.exists():
                # images.tar exists on host but not in container view
                images_host = Path(images_host_str)
                target_images = target_tmp_dir / "images.tar"
                shutil.copy2(images_host, target_images)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Copied images.tar from host: {images_host_str} -> {target_images}")

            # Step 2: Write manifest and DONE marker
            self._write_replication_manifest(target_tmp_dir, pack_dir.name, job_id)
            done_marker = target_tmp_dir / "DONE"
            done_marker.touch()
            self.store.update_job(job_id, message="复制完成（验证中）", progress=97)

            # Step 3: Atomic rename to final directory
            if target_final_dir.exists():
                shutil.rmtree(target_final_dir)
            target_final_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target_tmp_dir), str(target_final_dir))

            # Step 4: Update job message
            self.store.update_job(
                job_id,
                message="备份完成（已同步）",
                progress=100
            )
            return True

        except Exception as e:
            # Replication failed, but backup is still completed
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Replication failed: {e}", exc_info=True)

            self.store.update_job(
                job_id,
                message=f"备份完成（同步失败：{str(e)}）",
                detail=str(e),
                progress=100
            )
            return False

    def _generate_subdir(self, pack_name: str, format_type: str) -> str:
        """Generate subdirectory based on format."""
        if format_type == "date":
            # YYYY/MM/DD/migration_pack_xxx
            now = datetime.now()
            date_path = now.strftime("%Y/%m/%d")
            return str(Path(date_path) / pack_name)
        else:
            # flat: migration_pack_xxx
            return pack_name

    def _convert_to_host_path(self, path: Path) -> Path:
        """Convert container path to host path.

        Prefer dynamic mount inspection (via `docker inspect`) to avoid hardcoded host paths.
        """
        return Path(container_path_to_host_str(path))

    def _copy_directory(self, src: Path, dst: Path, job_id: int):
        """Copy directory recursively with progress updates."""
        ensure_dir(dst)

        # Special handling: check for volumes directory on host path
        volumes_container = src / "volumes"
        volumes_host = Path(container_path_to_host_str(volumes_container))

        # Count files including those on host path
        total_files = 0
        for root, dirs, files in os.walk(src):
            total_files += len(files)

        # Add volumes files from host path if they exist there but not in container
        if volumes_host.exists() and not volumes_container.exists():
            volumes_files = list(volumes_host.rglob("*"))
            volumes_files = [f for f in volumes_files if f.is_file()]
            total_files += len(volumes_files)

        if total_files == 0:
            return

        copied_files = 0
        # First, copy all files visible in container
        for root, dirs, files in os.walk(src):
            for file in files:
                src_file = Path(root) / file
                rel_path = src_file.relative_to(src)
                dst_file = dst / rel_path

                # Create parent directory if needed
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                # Special handling for files saved to host path (not container path)
                # This includes: images.tar and volumes/*.tar.gz
                src_file_to_copy = src_file
                if not src_file.exists():
                    src_file_to_copy = Path(container_path_to_host_str(src_file))

                # Copy file
                if src_file_to_copy.exists():
                    shutil.copy2(src_file_to_copy, dst_file)
                    copied_files += 1

        # Second, copy volumes files from host path if they exist there but are empty in container
        if volumes_host.exists():
            # Check if volumes directory in container is actually empty (or has no files)
            container_has_volumes_files = False
            if volumes_container.exists():
                container_volumes_files = list(volumes_container.rglob("*"))
                container_volumes_files = [f for f in container_volumes_files if f.is_file()]
                container_has_volumes_files = len(container_volumes_files) > 0

            # Copy from host if container doesn't have the files
            if not container_has_volumes_files:
                for src_file in volumes_host.rglob("*"):
                    if src_file.is_file():
                        rel_path = src_file.relative_to(volumes_host)
                        dst_file = dst / "volumes" / rel_path

                        # Create parent directory if needed
                        dst_file.parent.mkdir(parents=True, exist_ok=True)

                        # Copy file
                        shutil.copy2(src_file, dst_file)
                        copied_files += 1

                if total_files > 0:
                    progress = 92 + int(5 * copied_files / total_files)
        # Last resort: use docker run to copy volumes from the host via the docker socket
        volumes_on_host_str = container_path_to_host_str(volumes_container)

        # Get the current running container's image to use for docker run
        from .common import run_cmd
        helper_image = "ragflowauth-backend:latest"
        try:
            code, out = run_cmd(["docker", "ps", "--filter", "name=ragflowauth-backend", "--format", "{{.Image}}"])
            if code == 0 and out and out.strip():
                helper_image = out.strip()
        except Exception:
            pass  # Use fallback default

        try:
            # Ensure destination volumes directory exists
            dst_volumes = dst / "volumes"
            dst_volumes.mkdir(parents=True, exist_ok=True)

            # Copy individual files using docker run (more reliable than recursive copy)
            # First, list the files on host using docker run
            list_cmd = [
                "docker", "run", "--rm",
                "-v", f"{volumes_on_host_str}:/src:ro",
                helper_image,
                "sh", "-c", "ls -1 /src/*.tar.gz 2>/dev/null || echo ''"
            ]
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout.strip():
                files_to_copy = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                for filename in files_to_copy:
                    # Copy each file individually
                    copy_cmd = [
                        "docker", "run", "--rm",
                        "-v", f"{volumes_on_host_str}:/src:ro",
                        "-v", f"{dst}:/dst",
                        helper_image,
                        "sh", "-c", f"cp /src/{Path(filename).name} /dst/volumes/ 2>/dev/null || true"
                    ]
                    result2 = subprocess.run(copy_cmd, capture_output=True, timeout=60)
                    if result2.returncode == 0:
                        copied_files += 1

                if files_to_copy:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Copied {len(files_to_copy)} volume files from host: {volumes_on_host_str}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to copy volumes from host path {volumes_on_host_str}: {e}")
        # No additional "alt path" probing needed when container->host mapping is correct.

            if total_files > 0:
                progress = 92 + int(5 * copied_files / total_files)
                self.store.update_job(job_id, progress=progress)

    def _write_replication_manifest(self, target_dir: Path, pack_name: str, job_id: int):
        """Write replication manifest file."""
        manifest = {
            "pack_name": pack_name,
            "replicated_at_ms": int(time.time() * 1000),
            "replicated_at": datetime.now().isoformat(),
            "job_id": job_id,
            "source_hostname": os.uname().nodename,
        }

        manifest_file = target_dir / "replication_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
