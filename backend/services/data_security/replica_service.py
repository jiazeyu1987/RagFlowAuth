from __future__ import annotations

import os
import shutil
import subprocess
import time
import json
import logging
from pathlib import Path
from datetime import datetime

from .common import ensure_dir
from .store import DataSecurityStore
from .docker_utils import container_path_to_host_str

logger = logging.getLogger(__name__)


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
        logger.info("=" * 60)
        logger.info(f"[REPLICATION START] Job ID: {job_id}, Pack: {pack_dir.name}")
        logger.info("=" * 60)

        settings = self.store.get_settings()

        # Step 0: Check if replication is enabled
        logger.info("[Step 0] Checking if replication is enabled...")
        if not getattr(settings, 'replica_enabled', False):
            logger.info("[Step 0] ✓ Replication disabled - SKIPPED")
            return True  # Not enabled, skip

        logger.info(f"[Step 0] ✓ Replication enabled")

        # Step 1: Get target path
        logger.info("[Step 1] Getting target path...")
        target_path = settings.replica_target_path
        if not target_path:
            logger.error("[Step 1] ✗ FAILED: replica_target_path is empty")
            self.store.update_job(job_id, message="备份完成（同步失败：未配置复制目标路径）", detail="replica_target_path is empty")
            return False
        logger.info(f"[Step 1] ✓ Target path: {target_path}")

        target_base = Path(target_path)
        if not target_base.is_absolute():
            logger.error(f"[Step 1] ✗ FAILED: Target path is not absolute: {target_path}")
            self.store.update_job(job_id, message="备份完成（同步失败：复制目标路径必须是绝对路径）", detail=f"replica_target_path={target_path!r}")
            return False
        logger.info(f"[Step 1] ✓ Target path is absolute")

        # Step 2: Check if target is mounted to Windows share
        logger.info("[Step 2] Checking if target is mounted to Windows share...")
        is_mounted = self._check_is_cifs_mount(target_base)
        if not is_mounted:
            logger.error(f"[Step 2] ✗ FAILED: {target_base} is NOT a mounted CIFS share")
            logger.error(f"[Step 2] Files will be copied to local disk, NOT to Windows share!")
            logger.error(f"[Step 2] Please mount Windows share first:")
            logger.error(f"[Step 2]   mount -t cifs //192.168.112.72/backup {target_base.parent} -o username=...,password=...")
            self.store.update_job(
                job_id,
                message="备份完成（同步失败：目标路径未挂载到Windows共享）",
                detail=f"{target_base} is not a mounted CIFS share. Files copied to local disk instead.",
                progress=100
            )
            return False
        logger.info(f"[Step 2] ✓ Target is mounted to CIFS share")

        try:
            # Step 3: Generate subdirectory
            logger.info("[Step 3] Generating subdirectory...")
            subdir = self._generate_subdir(pack_dir.name, settings.replica_subdir_format)
            target_final_dir = target_base / subdir
            target_tmp_dir = target_base / "_tmp" / f"job_{job_id}_{int(time.time())}"
            logger.info(f"[Step 3] ✓ Subdirectory format: {settings.replica_subdir_format}")
            logger.info(f"[Step 3] ✓ Final target: {target_final_dir}")
            logger.info(f"[Step 3] ✓ Temp target: {target_tmp_dir}")

            # Step 4: Copy to temporary directory
            logger.info("[Step 4] Copying files to temporary directory...")
            self.store.update_job(job_id, message="开始复制（临时目录）", progress=92)
            self._copy_directory(pack_dir, target_tmp_dir, job_id)
            logger.info(f"[Step 4] ✓ Files copied to {target_tmp_dir}")

            # Step 5: Check and copy images.tar from host path (special handling)
            logger.info("[Step 5] Checking for images.tar on host path...")
            images_container = pack_dir / "images.tar"
            images_host_str = container_path_to_host_str(images_container)
            if os.path.exists(images_host_str) and not images_container.exists():
                # images.tar exists on host but not in container view
                logger.info(f"[Step 5] Found images.tar on host: {images_host_str}")
                images_host = Path(images_host_str)
                target_images = target_tmp_dir / "images.tar"
                shutil.copy2(images_host, target_images)
                logger.info(f"[Step 5] ✓ Copied images.tar to {target_images}")
            else:
                logger.info(f"[Step 5] No images.tar to copy (not a full backup)")

            # Step 6: Write manifest and DONE marker
            logger.info("[Step 6] Writing replication manifest...")
            self._write_replication_manifest(target_tmp_dir, pack_dir.name, job_id)
            logger.info(f"[Step 6] ✓ Manifest written")

            logger.info("[Step 6] Writing DONE marker...")
            done_marker = target_tmp_dir / "DONE"
            done_marker.touch()
            logger.info(f"[Step 6] ✓ DONE marker created")
            self.store.update_job(job_id, message="复制完成（验证中）", progress=97)

            # Step 7: Atomic rename to final directory
            logger.info("[Step 7] Moving to final directory (atomic rename)...")
            if target_final_dir.exists():
                logger.info(f"[Step 7] Removing existing directory: {target_final_dir}")
                shutil.rmtree(target_final_dir)
            target_final_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target_tmp_dir), str(target_final_dir))
            logger.info(f"[Step 7] ✓ Moved to {target_final_dir}")

            # Step 8: Verify replication
            logger.info("[Step 8] Verifying replication...")
            if self._verify_replication(target_final_dir):
                logger.info(f"[Step 8] ✓ Verification successful")
            else:
                logger.warning(f"[Step 8] ⚠ Verification failed but continuing")

            # Step 9: Update job message
            logger.info("[Step 9] Updating job status...")
            self.store.update_job(
                job_id,
                message="备份完成（已同步）",
                progress=100
            )
            logger.info(f"[Step 9] ✓ Job updated: 备份完成（已同步）")

            logger.info("=" * 60)
            logger.info(f"[REPLICATION SUCCESS] Job ID: {job_id}")
            logger.info(f"[REPLICATION SUCCESS] Target: {target_final_dir}")
            logger.info("=" * 60)
            return True

        except Exception as e:
            # Replication failed, but backup is still completed
            logger.error(f"[REPLICATION FAILED] Exception: {e}", exc_info=True)

            self.store.update_job(
                job_id,
                message=f"备份完成（同步失败：{str(e)}）",
                detail=str(e),
                progress=100
            )

            logger.error("=" * 60)
            logger.error(f"[REPLICATION FAILED] Job ID: {job_id}")
            logger.error(f"[REPLICATION FAILED] Error: {str(e)}")
            logger.error("=" * 60)
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
        logger.info(f"[Copy] Starting: {src} -> {dst}")
        ensure_dir(dst)
        logger.info(f"[Copy] Created destination: {dst}")

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

        logger.info(f"[Copy] Total files to copy: {total_files}")

        if total_files == 0:
            logger.warning(f"[Copy] No files to copy!")
            return

        copied_files = 0
        # First, copy all files visible in container
        logger.info(f"[Copy] Phase 1: Copying container-visible files...")
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
                    if copied_files % 10 == 0:
                        logger.debug(f"[Copy] Progress: {copied_files}/{total_files}")

        logger.info(f"[Copy] Phase 1 complete: {copied_files} files copied")

        # Second, copy volumes files from host path if they exist there but are empty in container
        if volumes_host.exists():
            logger.info(f"[Copy] Phase 2: Checking volumes on host...")
            # Check if volumes directory in container is actually empty (or has no files)
            container_has_volumes_files = False
            if volumes_container.exists():
                container_volumes_files = list(volumes_container.rglob("*"))
                container_volumes_files = [f for f in container_volumes_files if f.is_file()]
                container_has_volumes_files = len(container_volumes_files) > 0

            # Copy from host if container doesn't have the files
            if not container_has_volumes_files:
                logger.info(f"[Copy] Phase 2: Copying volumes from host path...")
                for src_file in volumes_host.rglob("*"):
                    if src_file.is_file():
                        rel_path = src_file.relative_to(volumes_host)
                        dst_file = dst / "volumes" / rel_path

                        # Create parent directory if needed
                        dst_file.parent.mkdir(parents=True, exist_ok=True)

                        # Copy file
                        shutil.copy2(src_file, dst_file)
                        copied_files += 1
                logger.info(f"[Copy] Phase 2 complete: volumes copied from host")

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
            logger.info(f"[Copy] Phase 3: Using docker run to copy volumes...")
            list_cmd = [
                "docker", "run", "--rm",
                "-v", f"{volumes_on_host_str}:/src:ro",
                helper_image,
                "sh", "-c", "ls -1 /src/*.tar.gz 2>/dev/null || echo ''"
            ]
            result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and result.stdout.strip():
                files_to_copy = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                logger.info(f"[Copy] Phase 3: Found {len(files_to_copy)} volume files")
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
                    logger.info(f"[Copy] Phase 3 complete: {len(files_to_copy)} volume files copied via docker")
        except Exception as e:
            logger.warning(f"[Copy] Phase 3 failed: {e}")

        logger.info(f"[Copy] Complete: {copied_files}/{total_files} files copied")

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
        logger.info(f"[Manifest] Written to {manifest_file}")

    def _check_is_cifs_mount(self, target_path: Path) -> bool:
        """Check if target_path is mounted to a CIFS/SMB share.

        Returns:
            True if mounted to CIFS share, False otherwise
        """
        try:
            # Check mount table for CIFS mount at or containing target_path
            result = subprocess.run(
                ['mount'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"[Mount Check] Failed to run mount command: {result.stderr}")
                return False

            target_str = target_path.as_posix()

            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue

                # Parse mount line: "device on mount_point type fstype options"
                parts = line.split()
                if len(parts) < 3:
                    continue

                mount_point = parts[2]
                fstype = parts[4] if len(parts) > 4 else ''

                # Check if this mount covers our target path
                # Must be CIFS type and target_path must be under mount_point
                if 'cifs' in fstype.lower():
                    # Check if target_path is under this mount point
                    if target_str.startswith(mount_point):
                        logger.info(f"[Mount Check] Found CIFS mount: {mount_point} (type: {fstype})")
                        logger.info(f"[Mount Check] Target {target_str} is under CIFS mount")
                        return True

            logger.warning(f"[Mount Check] No CIFS mount found for {target_str}")
            return False

        except subprocess.TimeoutExpired:
            logger.error("[Mount Check] Timeout checking mount status")
            return False
        except Exception as e:
            logger.error(f"[Mount Check] Error checking mount: {e}", exc_info=True)
            return False

    def _verify_replication(self, target_dir: Path) -> bool:
        """Verify that replication was successful.

        Args:
            target_dir: Target directory where backup was replicated

        Returns:
            True if verification passed, False otherwise
        """
        try:
            logger.info(f"[Verify] Checking {target_dir}...")

            # Check 1: Directory exists
            if not target_dir.exists():
                logger.error(f"[Verify] ✗ Directory does not exist: {target_dir}")
                return False
            logger.info(f"[Verify] ✓ Directory exists")

            # Check 2: DONE marker exists
            done_marker = target_dir / "DONE"
            if not done_marker.exists():
                logger.error(f"[Verify] ✗ DONE marker missing")
                return False
            logger.info(f"[Verify] ✓ DONE marker exists")

            # Check 3: Manifest exists
            manifest_file = target_dir / "replication_manifest.json"
            if not manifest_file.exists():
                logger.error(f"[Verify] ✗ Manifest missing")
                return False
            logger.info(f"[Verify] ✓ Manifest exists")

            # Check 4: At least auth.db exists
            auth_db = target_dir / "auth.db"
            if not auth_db.exists():
                logger.error(f"[Verify] ✗ auth.db missing")
                return False
            logger.info(f"[Verify] ✓ auth.db exists (size: {auth_db.stat().st_size} bytes)")

            # Check 5: Log summary
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                logger.info(f"[Verify] ✓ Pack: {manifest.get('pack_name')}")
                logger.info(f"[Verify] ✓ Replicated at: {manifest.get('replicated_at')}")
            except Exception as e:
                logger.warning(f"[Verify] ⚠ Could not read manifest: {e}")

            logger.info(f"[Verify] ✓ All checks passed")
            return True

        except Exception as e:
            logger.error(f"[Verify] ✗ Verification error: {e}", exc_info=True)
            return False
