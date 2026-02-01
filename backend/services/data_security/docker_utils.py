from __future__ import annotations

import json
import os
from pathlib import Path

from .common import ensure_dir, run_cmd, run_cmd_live


def _docker_self_mounts() -> list[dict]:
    """
    Best-effort: inspect the currently running container to learn bind-mount sources.

    This avoids hardcoding host paths like `/opt/ragflowauth/...` and fixes cases where
    `/app/data/backups` is mounted differently across environments.
    """
    cid = (os.environ.get("HOSTNAME") or "").strip()
    if not cid:
        return []

    code, out = run_cmd(["docker", "inspect", cid])
    if code != 0 or not out:
        return []

    try:
        data = json.loads(out)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            mounts = data[0].get("Mounts") or []
            if isinstance(mounts, list):
                return [m for m in mounts if isinstance(m, dict)]
    except Exception:
        return []

    return []


def container_path_to_host_str(path: str | Path) -> str:
    """
    Translate a container path (e.g. `/app/data/backups/...`) to the host path as seen by the Docker daemon.

    When we run `docker run`/`docker save` from inside the backend container (via docker socket),
    paths passed to docker CLI must be host paths, not container paths.
    """
    # Use raw string + POSIX normalization. This function deals with Linux container/daemon paths,
    # but the codebase can be developed on Windows (where `Path("/app")` becomes `\\app`).
    s = str(path).replace("\\", "/")
    if not s.startswith("/"):
        return s

    # Prefer dynamic mount inspection (no assumptions about host directory layout).
    mounts = _docker_self_mounts()
    best = None  # (dest, src)
    for m in mounts:
        dst = m.get("Destination")
        src = m.get("Source")
        if not isinstance(dst, str) or not isinstance(src, str) or not dst or not src:
            continue
        if s == dst or s.startswith(dst.rstrip("/") + "/"):
            if best is None or len(dst) > len(best[0]):
                best = (dst, src)

    if best is not None:
        dst, src = best
        suffix = s[len(dst) :]
        return f"{src}{suffix}"

    # Backward-compatible fallback for older deployments that used fixed host paths.
    host_backups = (os.environ.get("RAGFLOWAUTH_HOST_BACKUPS_DIR") or "/opt/ragflowauth/backups").rstrip("/")
    host_data = (os.environ.get("RAGFLOWAUTH_HOST_DATA_DIR") or "/opt/ragflowauth/data").rstrip("/")
    host_uploads = (os.environ.get("RAGFLOWAUTH_HOST_UPLOADS_DIR") or "/opt/ragflowauth/uploads").rstrip("/")

    if s.startswith("/app/data/backups"):
        return s.replace("/app/data/backups", host_backups, 1)
    if s.startswith("/app/data/") or s == "/app/data":
        return s.replace("/app/data", host_data, 1)
    if s.startswith("/app/uploads/") or s == "/app/uploads":
        return s.replace("/app/uploads", host_uploads, 1)
    return s


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


def docker_tar_volume(volume_name: str, dest_tar_gz: Path, *, heartbeat: callable | None = None) -> None:
    ensure_dir(dest_tar_gz.parent)
    backup_dir = dest_tar_gz.parent.resolve()

    backup_dir_str = container_path_to_host_str(backup_dir)

    # Get current running backend container's image (instead of hardcoded version)
    image = "ragflowauth-backend:latest"  # Fallback default
    try:
        code, out = run_cmd(["docker", "ps", "--filter", "name=ragflowauth-backend", "--format", "{{.Image}}"])
        if code == 0 and out and out.strip():
            image = out.strip()
    except Exception:
        pass  # Use fallback default

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/data:ro",
        "-v",
        f"{backup_dir_str}:/backup",
        image,
        "sh",
        "-lc",
        f"tar -czf /backup/{dest_tar_gz.name} -C /data .",
    ]
    code, out = run_cmd_live(cmd, heartbeat=heartbeat, heartbeat_interval_s=15.0)
    if code != 0:
        raise RuntimeError(f"备份 volume 失败：{volume_name}\n{out}")


def list_compose_images(compose_file: Path) -> tuple[list[str], str | None]:
    code, out = run_cmd(["docker", "compose", "-f", str(compose_file), "config", "--images"], cwd=compose_file.parent)
    if code != 0:
        return [], out or "docker compose config --images failed"
    images = sorted({line.strip() for line in (out or "").splitlines() if line.strip()})
    return images, None


def docker_save_images(images: list[str], dest_tar: Path, *, heartbeat: callable | None = None) -> tuple[bool, str | None]:
    if not images:
        return False, None

    # Ensure the container-visible directory exists (and therefore host dir exists if mounted).
    ensure_dir(dest_tar.parent)

    # IMPORTANT:
    # `docker save -o <path>` writes the output file on the machine that runs the docker CLI.
    # In our architecture the docker CLI runs *inside the backend container* (using docker.sock),
    # so the output path MUST be a container-visible path (typically under a bind mount like `/app/data/backups`).
    # Do NOT translate to a host-only path like `/opt/...`, otherwise the file can't be created.
    dest_tar_str = str(dest_tar).replace("\\", "/")

    code, out = run_cmd_live(["docker", "save", "-o", dest_tar_str, *images], heartbeat=heartbeat, heartbeat_interval_s=15.0)
    if code != 0:
        return False, out or "docker save failed"

    # Verify file was created (inside container filesystem)
    import os
    if os.path.exists(dest_tar_str):
        size = os.path.getsize(dest_tar_str)
    else:
        return False, f"File not created: {dest_tar_str}"

    return True, None


def list_running_container_images(*, name_prefix: str) -> list[str]:
    """
    Best-effort: list unique images of containers whose names start with `name_prefix`.

    Used as a fallback when `docker compose config --images` fails (e.g. missing env vars).
    """
    name_prefix_raw = str(name_prefix or "").strip()
    if not name_prefix_raw:
        return []
    base_prefix = name_prefix_raw.rstrip("_-")
    if not base_prefix:
        return []

    code, out = run_cmd(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}"])
    if code != 0:
        return []

    images: list[str] = []
    for line in (out or "").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        name, image = line.split("\t", 1)
        name = name.strip()
        image = image.strip()
        if not (
            name == base_prefix
            or name.startswith(base_prefix + "_")
            or name.startswith(base_prefix + "-")
            or name.startswith(name_prefix_raw)
        ):
            continue
        if not image or "<none>" in image:
            continue
        if image not in images:
            images.append(image)

    return images
