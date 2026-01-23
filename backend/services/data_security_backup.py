from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

from backend.app.core.paths import repo_root
from backend.services.data_security_store import DataSecurityStore


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _docker_ok() -> tuple[bool, str]:
    code, out = _run(["docker", "info"])
    if code != 0:
        return False, out or "Docker 引擎不可用"
    code, out = _run(["docker", "compose", "version"])
    if code != 0:
        return False, out or "docker compose 命令不可用"
    return True, ""


def _docker_compose_stop(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "stop"], cwd=compose_file.parent)
    if code != 0:
        raise RuntimeError(f"停止 RAGFlow 服务失败：{out}")


def _docker_compose_start(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "start"], cwd=compose_file.parent)
    if code != 0:
        raise RuntimeError(f"启动 RAGFlow 服务失败：{out}")


def _list_docker_volumes_by_prefix(prefix: str) -> list[str]:
    code, out = _run(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(f"无法读取 Docker volumes：{out}")
    vols: list[str] = []
    for line in (out or "").splitlines():
        name = line.strip()
        if name.startswith(prefix):
            vols.append(name)
    return sorted(vols)


def _read_compose_project_name(compose_file: Path) -> str:
    """
    Infer compose project name (best-effort):
    - top-level `name:` in docker compose YAML (if pyyaml installed)
    - `.env` next to compose file: `COMPOSE_PROJECT_NAME=...`
    - fallback: compose file parent folder name
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(compose_file.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    except Exception:
        pass

    env_file = compose_file.parent / ".env"
    try:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "COMPOSE_PROJECT_NAME" and v.strip():
                    return v.strip().strip('"').strip("'")
    except Exception:
        pass

    return compose_file.parent.name


def _docker_tar_volume(volume_name: str, dest_tar_gz: Path) -> None:
    _ensure_dir(dest_tar_gz.parent)
    # Ensure paths are absolute for Docker volume mounting
    backup_dir = dest_tar_gz.parent.resolve()

    # Convert container path to host path for Docker-in-Docker scenario
    # /app/data/... -> /opt/ragflowauth/data/...
    backup_dir_str = str(backup_dir)
    if backup_dir_str.startswith("/app/data/"):
        backup_dir_str = backup_dir_str.replace("/app/data", "/opt/ragflowauth/data", 1)
    elif backup_dir_str.startswith("/app/uploads/"):
        backup_dir_str = backup_dir_str.replace("/app/uploads", "/opt/ragflowauth/uploads", 1)

    # Use ragflowauth-backend:local which already exists on server
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/data:ro",
        "-v",
        f"{backup_dir_str}:/backup",
        "ragflowauth-backend:local",
        "sh",
        "-lc",
        f"tar -czf /backup/{dest_tar_gz.name} -C /data .",
    ]
    code, out = _run(cmd)
    if code != 0:
        raise RuntimeError(f"备份 volume 失败：{volume_name}\n{out}")


def _list_compose_images(compose_file: Path) -> tuple[list[str], str | None]:
    """
    Best effort list of images used by a compose file.
    Uses `docker compose config --images` so it can resolve `.env` in the same folder.
    Returns (images, error_message).
    """
    code, out = _run(["docker", "compose", "-f", str(compose_file), "config", "--images"], cwd=compose_file.parent)
    if code != 0:
        return [], out or "docker compose config --images failed"
    images = sorted({line.strip() for line in (out or "").splitlines() if line.strip()})
    return images, None


def _docker_save_images(images: list[str], dest_tar: Path) -> tuple[bool, str | None]:
    if not images:
        return False, None

    # Convert container path to host path for Docker-in-Docker scenario
    dest_tar_str = str(dest_tar)
    if dest_tar_str.startswith("/app/data/"):
        dest_tar_str = dest_tar_str.replace("/app/data", "/opt/ragflowauth/data", 1)
    elif dest_tar_str.startswith("/app/uploads/"):
        dest_tar_str = dest_tar_str.replace("/app/uploads", "/opt/ragflowauth/uploads", 1)

    _ensure_dir(Path(dest_tar_str).parent)

    code, out = _run(["docker", "save", "-o", dest_tar_str, *images])
    if code != 0:
        return False, out or "docker save failed"
    return True, None


def _sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    _ensure_dir(dest_db.parent)
    src = sqlite3.connect(str(src_db))
    try:
        dst = sqlite3.connect(str(dest_db))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


class DataSecurityBackupService:
    def __init__(self, store: DataSecurityStore) -> None:
        self.store = store

    def run_job(self, job_id: int) -> None:
        settings = self.store.get_settings()
        target = settings.target_path()
        if not target:
            raise RuntimeError("未配置备份目标（请设置目标电脑IP/共享目录，或选择本地目录）")

        ok, why = _docker_ok()
        if not ok:
            raise RuntimeError(f"Docker 不可用：{why}")

        now_ms = int(time.time() * 1000)
        self.store.update_job(job_id, status="running", progress=1, message="开始备份", started_at_ms=now_ms)

        pack_dir = Path(target) / f"migration_pack_{_timestamp()}"
        _ensure_dir(pack_dir)
        self.store.update_job(job_id, output_dir=str(pack_dir), message="创建迁移包目录", progress=3)

        # 1) auth.db
        src_db = Path(settings.auth_db_path)
        if not src_db.is_absolute():
            src_db = repo_root() / src_db
        if not src_db.exists():
            raise RuntimeError(f"找不到本项目数据库：{src_db}")
        self.store.update_job(job_id, message="备份本项目数据库", progress=10)
        _sqlite_online_backup(src_db, pack_dir / "auth.db")
        self.store.update_job(job_id, message="本项目数据库已写入", progress=35)

        # 2) ragflow volumes
        compose_path = (settings.ragflow_compose_path or "").strip()
        if not compose_path:
            raise RuntimeError("未设置 RAGFlow docker-compose.yml 路径（请在“数据安全”里选择）")
        compose_file = Path(compose_path)
        if not compose_file.is_absolute():
            compose_file = repo_root() / compose_file
        if not compose_file.exists():
            raise RuntimeError(f"找不到 RAGFlow docker-compose.yml：{compose_file}")

        project = _read_compose_project_name(compose_file)
        prefix = f"{project}_"

        ragflow_dir = pack_dir / "ragflow"
        vols_dir = ragflow_dir / "volumes"
        images_dir = ragflow_dir / "images"
        _ensure_dir(vols_dir)
        _ensure_dir(images_dir)

        try:
            (ragflow_dir / "docker-compose.yml").write_bytes(compose_file.read_bytes())
        except Exception:
            pass

        stop = bool(settings.ragflow_stop_services)
        if stop:
            self.store.update_job(job_id, message="停止 RAGFlow 服务", progress=40)
            _docker_compose_stop(compose_file)

        archives: list[str] = []
        try:
            self.store.update_job(job_id, message="扫描 RAGFlow volumes", progress=45)
            vols = _list_docker_volumes_by_prefix(prefix)
            if not vols:
                raise RuntimeError(
                    f"找不到 RAGFlow volumes（前缀 {prefix}）。请确认该 compose 对应的 RAGFlow 已在本机启动过。"
                )

            per = max(1, int(50 / max(1, len(vols))))
            prog = 50
            for v in vols:
                self.store.update_job(job_id, message=f"打包 volume：{v}", progress=min(95, prog))
                name = f"{v}_{_timestamp()}.tar.gz"
                _docker_tar_volume(v, vols_dir / name)
                archives.append(name)
                prog += per
        finally:
            if stop:
                self.store.update_job(job_id, message="启动 RAGFlow 服务", progress=96)
                _docker_compose_start(compose_file)

        # 3) ragflow images (skipped - images can be pulled from registry)
        images: list[str] = []
        images_archives: list[str] = []
        images_note: str = "镜像导出已禁用，可从 Docker Hub 重新拉取"

        manifest = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "contains": {"auth_db": True, "ragflow": True},
            "auth_db": {"path": "auth.db"},
            "ragflow": {
                "compose_file": str(compose_file),
                "project_name": project,
                "volumes_prefix": prefix,
                "volumes_dir": "ragflow/volumes",
                "volume_archives": archives,
                "images_note": images_note,
            },
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        self.store.update_job(job_id, message="备份完成", progress=100)

        # 4) Upload to remote server if configured
        if getattr(settings, 'upload_after_backup', False):
            upload_host = getattr(settings, 'upload_host', '').strip()
            upload_username = getattr(settings, 'upload_username', '').strip()
            upload_target_path = getattr(settings, 'upload_target_path', '').strip()

            if upload_host and upload_username and upload_target_path:
                try:
                    self.store.update_job(job_id, message="上传备份到远程服务器", progress=98)

                    # Convert Windows path to SCP format (e.g., D:\datas -> /mnt/d/datas)
                    # For Windows OpenSSH, we can use Windows path directly
                    remote_path = upload_target_path.replace('\\', '/')

                    # Use scp to upload the entire pack directory
                    cmd = [
                        "scp",
                        "-r",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "UserKnownHostsFile=/dev/null",
                        str(pack_dir),
                        f"{upload_username}@{upload_host}:{remote_path}/"
                    ]

                    code, out = _run(cmd)
                    if code != 0:
                        raise RuntimeError(f"上传失败：{out}")

                    self.store.update_job(job_id, message="上传完成", progress=99)
                except Exception as e:
                    # Log error but don't fail the backup
                    import logging
                    logging.error(f"Upload to remote failed: {e}")
                    self.store.update_job(job_id, message=f"备份完成，但上传失败：{str(e)}", progress=100)

        done_ms = int(time.time() * 1000)
        if not getattr(settings, 'upload_after_backup', False) or not getattr(settings, 'upload_host', ''):
            self.store.update_job(job_id, status="success", progress=100, message="备份完成", finished_at_ms=done_ms)
        else:
            self.store.update_job(job_id, status="success", progress=100, message="备份完成并已上传", finished_at_ms=done_ms)

