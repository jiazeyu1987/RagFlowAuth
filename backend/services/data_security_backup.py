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


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _docker_ok() -> tuple[bool, str]:
    code, out = _run(["docker", "version"])
    if code != 0:
        return False, out or "docker 命令不可用"
    code, out = _run(["docker", "compose", "version"])
    if code != 0:
        return False, out or "docker compose 命令不可用"
    return True, ""


def _docker_compose_stop(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "stop"])
    if code != 0:
        raise RuntimeError(f"停止 RAGFlow 服务失败：{out}")


def _docker_compose_start(compose_file: Path) -> None:
    code, out = _run(["docker", "compose", "-f", str(compose_file), "start"])
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


def _read_compose_project_name(compose_file: Path) -> str | None:
    """
    Tries to infer compose project name from:
    - top-level `name:` in docker compose YAML
    - `.env` next to compose file: `COMPOSE_PROJECT_NAME=...`
    - docker volumes suffix matching (best effort)
    - fallback: compose file parent folder name
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(compose_file.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

            volume_keys: list[str] = []
            vols = data.get("volumes")
            if isinstance(vols, dict):
                for k in vols.keys():
                    if isinstance(k, str) and k.strip():
                        volume_keys.append(k.strip())

            if volume_keys:
                try:
                    code, out = _run(["docker", "volume", "ls", "--format", "{{.Name}}"])
                    if code == 0:
                        candidates: dict[str, int] = {}
                        for vol_name in (out or "").splitlines():
                            vol_name = vol_name.strip()
                            if not vol_name:
                                continue
                            for key in volume_keys:
                                suffix = f"_{key}"
                                if vol_name.endswith(suffix) and len(vol_name) > len(suffix):
                                    prefix = vol_name[: -len(suffix)]
                                    candidates[prefix] = candidates.get(prefix, 0) + 1
                        if candidates:
                            best = sorted(candidates.items(), key=lambda x: (-x[1], x[0]))[0][0]
                            if best.strip():
                                return best.strip()
                except Exception:
                    pass
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
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/data:ro",
        "-v",
        f"{str(dest_tar_gz.parent)}:/backup",
        "alpine",
        "sh",
        "-lc",
        f"tar -czf /backup/{dest_tar_gz.name} -C /data .",
    ]
    code, out = _run(cmd)
    if code != 0:
        raise RuntimeError(f"备份 volume 失败：{volume_name}\n{out}")


def _sqlite_online_backup(src_db: Path, dest_db: Path) -> None:
    _ensure_dir(dest_db.parent)
    src = sqlite3.connect(str(src_db))
    try:
        try:
            src.execute("PRAGMA wal_checkpoint(FULL)")
        except sqlite3.OperationalError:
            pass
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
        _ensure_dir(vols_dir)
        try:
            (ragflow_dir / "docker-compose.yml").write_bytes(compose_file.read_bytes())
        except Exception:
            pass

        stop = bool(settings.ragflow_stop_services)
        if stop:
            self.store.update_job(job_id, message="停止 RAGFlow 服务", progress=40)
            _docker_compose_stop(compose_file)

        try:
            self.store.update_job(job_id, message="扫描 RAGFlow volumes", progress=45)
            vols = _list_docker_volumes_by_prefix(prefix)
            if not vols:
                raise RuntimeError(
                    f"找不到 RAGFlow volumes（前缀 {prefix}）。"
                    "请确认该 docker-compose.yml 对应的 RAGFlow 已在本机启动过。"
                    "如果你用过自定义 Compose 项目名，请在 compose 文件顶层增加 `name:`，或在同目录 `.env` 里设置 `COMPOSE_PROJECT_NAME=`。"
                )

            per = max(1, int(50 / max(1, len(vols))))
            prog = 50
            archives: list[str] = []
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

        manifest = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "contains": {"auth_db": True, "ragflow": True},
            "auth_db": {"path": "auth.db"},
            "ragflow": {
                "compose_file": str(compose_file),
                "project_name": project,
                "volumes_prefix": prefix,
                "volumes_dir": "ragflow/volumes",
            },
        }
        (pack_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        done_ms = int(time.time() * 1000)
        self.store.update_job(job_id, status="success", progress=100, message="备份完成", finished_at_ms=done_ms)
