from __future__ import annotations

from pathlib import Path

from .common import ensure_dir, run_cmd


def docker_ok() -> tuple[bool, str]:
    code, out = run_cmd(["docker", "info"])
    if code != 0:
        return False, out or "Docker 引擎不可用"
    code, out = run_cmd(["docker", "compose", "version"])
    if code != 0:
        return False, out or "docker compose 命令不可用"
    return True, ""


def docker_compose_stop(compose_file: Path) -> None:
    code, out = run_cmd(["docker", "compose", "-f", str(compose_file), "stop"], cwd=compose_file.parent)
    if code != 0:
        raise RuntimeError(f"停止 RAGFlow 服务失败：{out}")


def docker_compose_start(compose_file: Path) -> None:
    code, out = run_cmd(["docker", "compose", "-f", str(compose_file), "start"], cwd=compose_file.parent)
    if code != 0:
        raise RuntimeError(f"启动 RAGFlow 服务失败：{out}")


def list_docker_volumes_by_prefix(prefix: str) -> list[str]:
    code, out = run_cmd(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if code != 0:
        raise RuntimeError(f"无法读取 Docker volumes：{out}")
    vols: list[str] = []
    for line in (out or "").splitlines():
        name = line.strip()
        if name.startswith(prefix):
            vols.append(name)
    return sorted(vols)


def read_compose_project_name(compose_file: Path) -> str:
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


def docker_tar_volume(volume_name: str, dest_tar_gz: Path) -> None:
    ensure_dir(dest_tar_gz.parent)
    backup_dir = dest_tar_gz.parent.resolve()

    backup_dir_str = str(backup_dir)
    if backup_dir_str.startswith("/app/data/backups/"):
        backup_dir_str = backup_dir_str.replace("/app/data/backups", "/opt/ragflowauth/backups", 1)
    elif backup_dir_str.startswith("/app/data/"):
        backup_dir_str = backup_dir_str.replace("/app/data", "/opt/ragflowauth/data", 1)
    elif backup_dir_str.startswith("/app/uploads/"):
        backup_dir_str = backup_dir_str.replace("/app/uploads", "/opt/ragflowauth/uploads", 1)

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
    code, out = run_cmd(cmd)
    if code != 0:
        raise RuntimeError(f"备份 volume 失败：{volume_name}\n{out}")


def list_compose_images(compose_file: Path) -> tuple[list[str], str | None]:
    code, out = run_cmd(["docker", "compose", "-f", str(compose_file), "config", "--images"], cwd=compose_file.parent)
    if code != 0:
        return [], out or "docker compose config --images failed"
    images = sorted({line.strip() for line in (out or "").splitlines() if line.strip()})
    return images, None


def docker_save_images(images: list[str], dest_tar: Path) -> tuple[bool, str | None]:
    if not images:
        return False, None

    dest_tar_str = str(dest_tar)
    if dest_tar_str.startswith("/app/data/"):
        dest_tar_str = dest_tar_str.replace("/app/data", "/opt/ragflowauth/data", 1)
    elif dest_tar_str.startswith("/app/uploads/"):
        dest_tar_str = dest_tar_str.replace("/app/uploads", "/opt/ragflowauth/uploads", 1)

    ensure_dir(Path(dest_tar_str).parent)

    code, out = run_cmd(["docker", "save", "-o", dest_tar_str, *images])
    if code != 0:
        return False, out or "docker save failed"
    return True, None

