from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, TEST_SERVER_IP
from tool.maintenance.features.release_publish import (
    DEFAULT_REMOTE_APP_DIR,
    PublishResult,
    ServerVersionInfo,
    bootstrap_server_containers,
    docker_load_tar_on_server,
    get_server_version_info,
    preflight_check_ragflow_base_url,
    recreate_server_containers_from_inspect,
)


def _run_local(command: str, *, cwd: Path | None = None, timeout_s: int = 3600) -> tuple[bool, str]:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return (proc.returncode == 0), out.strip()


def publish_from_local_to_test(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    healthcheck_url: str = "http://127.0.0.1:8001/health",
) -> PublishResult:
    """
    Publish local workspace build -> TEST server by:
    1) docker build backend+frontend locally with a shared tag
    2) docker save both images to a single tar
    3) scp tar to TEST
    4) docker load on TEST
    5) recreate TEST containers from inspect with the new images
    """
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_lines.append(f"[{ts}] {msg}")

    def finish(ok: bool, before: ServerVersionInfo | None, after: ServerVersionInfo | None) -> PublishResult:
        return PublishResult(ok=ok, log="\n".join(log_lines), version_before=before, version_after=after)

    tag = (version or time.strftime("%Y%m%d_%H%M%S", time.localtime())).strip()
    backend_image = f"ragflowauth-backend:{tag}"
    frontend_image = f"ragflowauth-frontend:{tag}"

    repo_root = Path(__file__).resolve().parents[3]

    before = get_server_version_info(server_ip=test_ip, app_dir=app_dir)
    log(f"LOCAL -> TEST={test_ip} VERSION={tag}")

    if not preflight_check_ragflow_base_url(
        server_ip=test_ip,
        expected_server_ip=test_ip,
        app_dir=app_dir,
        log=log,
        role_name="TEST",
    ):
        log("[ERROR] Preflight check failed; refusing to publish (to avoid TEST reading PROD datasets).")
        return finish(False, before, None)

    log("[1/6] Build images locally")
    ok, out = _run_local(f'docker build -f backend/Dockerfile -t {backend_image} .', cwd=repo_root, timeout_s=7200)
    if not ok:
        log(f"[ERROR] build backend failed:\n{out}")
        return finish(False, before, None)
    ok, out = _run_local(f'docker build -f fronted/Dockerfile -t {frontend_image} .', cwd=repo_root, timeout_s=7200)
    if not ok:
        log(f"[ERROR] build frontend failed:\n{out}")
        return finish(False, before, None)

    log("[2/6] Export images locally (docker save)")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ragflowauth_release_"))
    tar_local = tmp_dir / f"ragflowauth_release_{tag}.tar"
    ok, out = _run_local(f'docker save {backend_image} {frontend_image} -o "{tar_local}"', timeout_s=7200)
    if not ok or not tar_local.exists():
        log(f"[ERROR] docker save failed:\n{out}")
        return finish(False, before, None)

    tar_on_test = f"/tmp/ragflowauth_release_{tag}.tar"
    log("[3/6] Transfer images to TEST (scp)")
    log(f"scp tar: {tar_local} -> {DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}")
    ok, out = _run_local(f'scp "{tar_local}" {DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}', timeout_s=7200)
    if not ok:
        log(f"[ERROR] scp failed:\n{out}")
        return finish(False, before, None)

    log("[4/6] Load images on TEST (docker load)")
    ok, out = docker_load_tar_on_server(server_ip=test_ip, tar_path=tar_on_test)
    if not ok:
        log(f"[ERROR] docker load failed:\n{out}")
        return finish(False, before, None)

    log("[5/6] Recreate TEST containers with local images")
    ok, msg = recreate_server_containers_from_inspect(
        server_ip=test_ip,
        backend_image=backend_image,
        frontend_image=frontend_image,
        healthcheck_url=healthcheck_url,
        log=log,
    )
    if not ok:
        if "containers not found" in (msg or ""):
            log("[WARN] TEST containers not found; this looks like first-time deploy. Falling back to bootstrap mode.")
            ok2, msg2 = bootstrap_server_containers(
                server_ip=test_ip,
                backend_image=backend_image,
                frontend_image=frontend_image,
                healthcheck_url=healthcheck_url,
                log=log,
                app_dir=app_dir,
            )
            if not ok2:
                log(f"[ERROR] bootstrap failed: {msg2}")
                return finish(False, before, None)
        else:
            log(f"[ERROR] recreate failed: {msg}")
            return finish(False, before, None)

    log("[6/6] Done")
    after = get_server_version_info(server_ip=test_ip, app_dir=app_dir)
    log("Publish completed")
    return finish(True, before, after)
