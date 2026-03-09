from __future__ import annotations

import json
from typing import Callable


def read_ragflow_base_url(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], server_ip: str, app_dir: str) -> tuple[bool, str]:
    """
    Read base_url from ragflow_config.json on the target server.
    Uses POSIX tools (sed/head) so it works even when host python isn't installed.
    """
    cfg_path = f"{app_dir}/ragflow_config.json"
    cmd = (
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = ssh_cmd(server_ip, cmd)
    text = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if text == "MISSING":
        return False, f"missing {cfg_path}"
    if not ok:
        return False, (out or "").strip()
    if not text:
        return False, f"unable to parse base_url from {cfg_path}"
    return True, text


def preflight_check_ragflow_base_url(
    *,
    read_base_url_fn: Callable[[str, str], tuple[bool, str]],
    server_ip: str,
    expected_server_ip: str,
    app_dir: str,
    log,
    role_name: str,
) -> bool:
    """
    Guardrail: ensure a server's ragflow_config.json points to its own RAGFlow (or localhost),
    so TEST doesn't read PROD and vice versa.
    """
    ok, base_url_or_err = read_base_url_fn(server_ip, app_dir)
    if not ok:
        log(f"[PRECHECK] [ERROR] {role_name} ragflow_config base_url check failed: {base_url_or_err}")
        log(f"[PRECHECK] Hint: ensure {app_dir}/ragflow_config.json exists on {server_ip}.")
        return False

    base_url = base_url_or_err.strip()
    log(f"[PRECHECK] {role_name} ragflow base_url: {base_url}")

    allowed = (expected_server_ip in base_url) or ("localhost" in base_url) or ("127.0.0.1" in base_url)
    if not allowed:
        log(f"[PRECHECK] [ERROR] {role_name} ragflow_config.json base_url looks wrong.")
        log(f"[PRECHECK] Expected to contain '{expected_server_ip}' (or localhost), got: {base_url}")
        return False
    return True


def docker_inspect(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], ip: str, container_name: str) -> dict | None:
    ok, out = ssh_cmd(ip, f"docker inspect {container_name} 2>/dev/null || echo '[]'")
    if not ok:
        return None
    text = (out or "").strip()
    try:
        data = json.loads(text)
    except Exception:
        return None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def detect_ragflow_images_on_server(*, ssh_cmd: Callable[[str, str], tuple[bool, str]], server_ip: str) -> list[str]:
    """
    Best-effort detection of RAGFlow container images on a server.

    We only need image tags (strings) so we can optionally include them in docker save/load.
    This helps when PROD can't pull from internet (offline) and the local image cache gets deleted/corrupted.
    """
    # Prefer containers created by /opt/ragflowauth/ragflow_compose (commonly named ragflow_compose-*).
    ok, out = ssh_cmd(
        server_ip,
        "docker ps --format '{{.Names}}\t{{.Image}}' | grep -E '^ragflow_compose-.*ragflow' || true",
    )
    images: list[str] = []
    if ok and out:
        for line in (out or "").splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                img = parts[1].strip()
                if img and img not in images:
                    images.append(img)

    # Fallback: detect common upstream image name if container naming differs.
    if not images:
        ok, out = ssh_cmd(
            server_ip,
            "docker ps --format '{{.Image}}' | grep -E '^infiniflow/ragflow:' | head -n 5 || true",
        )
        if ok and out:
            for img in (out or "").splitlines():
                img = img.strip()
                if img and img not in images:
                    images.append(img)

    return images
