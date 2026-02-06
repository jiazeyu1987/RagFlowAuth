from __future__ import annotations

import subprocess
import time
from pathlib import Path

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, TEST_SERVER_IP
from tool.maintenance.core.remote_staging import RemoteStagingManager
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
    # Strip known noisy lines that can appear on some Windows OpenSSH builds.
    out = "\n".join(
        line
        for line in out.splitlines()
        if not line.startswith("close - IO is still pending on closed socket.")
    )
    return (proc.returncode == 0), out.strip()


def _ssh(server_ip: str, command: str, *, timeout_s: int = 60) -> tuple[bool, str]:
    # Keep it simple: rely on OpenSSH on the local machine.
    # Note: command must be a single shell string executed remotely.
    return _run_local(
        f'ssh -o BatchMode=yes -o ConnectTimeout=10 {DEFAULT_SERVER_USER}@{server_ip} "{command}"',
        timeout_s=timeout_s,
    )


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
    ok, out = _run_local(f'scp "{tar_local}" {DEFAULT_SERVER_USER}@{test_ip}:{tar_on_test}', timeout_s=7200)
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
