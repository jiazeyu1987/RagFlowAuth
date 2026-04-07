from __future__ import annotations

import subprocess
import time
from pathlib import Path

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, TEST_SERVER_IP
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.core.ssh_executor import build_scp_argv, build_ssh_argv
from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir
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

_BUILD_BASE_IMAGES: tuple[str, ...] = (
    "python:3.12-slim",
    "node:20-alpine",
    "nginx:1.27-alpine",
)


def _run_local(command: str, *, cwd: Path | None = None, timeout_s: int = 3600) -> tuple[bool, str]:
    try:
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
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout_s} seconds"
    out = (proc.stdout or "") + (proc.stderr or "")
    # Strip known noisy lines that can appear on some Windows OpenSSH builds.
    out = "\n".join(
        line
        for line in out.splitlines()
        if not line.startswith("close - IO is still pending on closed socket.")
    )
    return (proc.returncode == 0), out.strip()


def _ssh(server_ip: str, command: str, *, timeout_s: int = 60) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            build_ssh_argv(user=DEFAULT_SERVER_USER, ip=server_ip, command=command),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout_s} seconds"
    out = (proc.stdout or "") + (proc.stderr or "")
    out = "\n".join(
        line
        for line in out.splitlines()
        if not line.startswith("close - IO is still pending on closed socket.")
    )
    return (proc.returncode == 0), out.strip()


def _pull_base_images_with_retries(*, images: tuple[str, ...], log, retries: int = 3, delay_s: int = 3) -> tuple[bool, str]:
    """
    Pull docker base images with bounded retries.
    We still fail fast when all retries are exhausted (no offline fallback).
    """
    for image in images:
        last_out = ""
        for attempt in range(1, retries + 1):
            ok, out = _run_local(f"docker pull {image}", timeout_s=1800)
            last_out = out
            if ok:
                log(f"[1/6] base image ready: {image}")
                break
            if attempt < retries:
                log(f"[WARN] pull base image failed ({image}) attempt {attempt}/{retries}, retrying...")
                time.sleep(delay_s)
        else:
            return False, f"pull base image failed ({image}) after {retries} attempts:\n{last_out}"
    return True, "OK"


def publish_from_local_to_test(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    healthcheck_url: str = "http://127.0.0.1:8001/health",
    ui_log=None,
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
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        if ui_log:
            try:
                ui_log(line)
            except Exception:
                # UI logging must never break the publish flow.
                pass

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
    log("[1/6] Pre-pull docker base images (retry up to 3 times)")
    ok, out = _pull_base_images_with_retries(images=_BUILD_BASE_IMAGES, log=log, retries=3, delay_s=3)
    if not ok:
        log(f"[ERROR] {out}")
        return finish(False, before, None)

    ok, out = _run_local(f'docker build -f backend/Dockerfile -t {backend_image} .', cwd=repo_root, timeout_s=7200)
    if not ok:
        log(f"[ERROR] build backend failed:\n{out}")
        return finish(False, before, None)
    ok, out = _run_local(f'docker build -f fronted/Dockerfile -t {frontend_image} .', cwd=repo_root, timeout_s=7200)
    if not ok:
        log(f"[ERROR] build frontend failed:\n{out}")
        return finish(False, before, None)

    log("[2/6] Export images locally (docker save)")
    tmp_dir = make_temp_dir(prefix="ragflowauth_release")
    tar_local = tmp_dir / f"ragflowauth_release_{tag}.tar"
    ok, out = _run_local(f'docker save {backend_image} {frontend_image} -o "{tar_local}"', timeout_s=7200)
    if not ok or not tar_local.exists():
        log(f"[ERROR] docker save failed:\n{out}")
        return finish(False, before, None)

    tar_size = int(tar_local.stat().st_size)
    log(f"[STAGING] local tar size: {tar_size} bytes")

    # Pick a remote staging location with enough free space.
    staging_mgr = RemoteStagingManager(exec_fn=lambda c: _ssh(test_ip, c, timeout_s=60), log=log)
    log("[CLEANUP] pre-clean legacy /tmp release artifacts on TEST (best-effort)")
    staging_mgr.cleanup_legacy_tmp_release_files()
    pick = staging_mgr.pick_dir_for_bytes(size_bytes=tar_size)
    tar_on_test = staging_mgr.join(pick.dir, f"ragflowauth_release_{tag}.tar")
    log(f"[STAGING] remote tar path: {tar_on_test}")
    log("[3/6] Transfer images to TEST (scp)")
    log(f"scp tar: {tar_local} -> {DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}")
    try:
        proc = subprocess.run(
            build_scp_argv(str(tar_local), f"{DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200,
        )
    except subprocess.TimeoutExpired:
        log("[ERROR] scp failed:\nCommand timed out after 7200 seconds")
        return finish(False, before, None)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    ok = proc.returncode == 0
    if not ok:
        log(f"[ERROR] scp failed:\n{out}")
        return finish(False, before, None)

    log("[4/6] Load images on TEST (docker load)")
    ok, out = docker_load_tar_on_server(server_ip=test_ip, tar_path=tar_on_test)
    if not ok:
        log(f"[ERROR] docker load failed:\n{out}")
        return finish(False, before, None)

    # Cleanup remote tar on success (avoid filling rootfs).
    log("[CLEANUP] remove remote staging tar on TEST")
    staging_mgr.cleanup_path(tar_on_test)

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

    # Cleanup local tar on success.
    try:
        tar_local.unlink(missing_ok=True)
    except Exception:
        pass
    cleanup_dir(tmp_dir)
    return finish(True, before, after)
