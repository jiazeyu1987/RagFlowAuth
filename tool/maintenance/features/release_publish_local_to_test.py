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

_REMOTE_STAGING_DIR_CANDIDATES = (
    # Prefer large, non-root partitions first.
    "/var/lib/docker/tmp",  # typically a dedicated docker disk (largest)
    "/mnt/replica/_tmp",  # optional: Windows share (large, but slower)
    "/home/root/_tmp",  # fallback when /home is separate
    "/tmp",  # LAST RESORT: often on rootfs (can be full)
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


def _remote_available_kb(server_ip: str, path: str) -> int | None:
    ok, out = _ssh(server_ip, f"df -Pk {path} 2>/dev/null | tail -n 1", timeout_s=20)
    if not ok:
        return None
    # Expected: Filesystem 1024-blocks Used Available Capacity Mounted on
    parts = (out or "").strip().split()
    if len(parts) < 4:
        return None
    try:
        return int(parts[3])
    except Exception:
        return None


def _remote_dir_writable(server_ip: str, path: str) -> tuple[bool, str]:
    cmd = (
        f"set -e; mkdir -p {path}; "
        f"t={path}/.ragflowauth_write_test_$$; "
        f"touch $t 2>/dev/null && rm -f $t && echo OK"
    )
    ok, out = _ssh(server_ip, cmd, timeout_s=20)
    if ok and ("OK" in (out or "")):
        return True, "OK"
    return False, (out or "").strip() or "not_writable"


def _pick_remote_tar_path(server_ip: str, *, tar_size_bytes: int, tag: str, log) -> str:
    need_kb = int((tar_size_bytes + 1024 * 1024 - 1) // (1024 * 1024)) * 1024  # round up to MB, in KB

    best_dir: str | None = None
    best_avail_kb: int = -1

    for d in _REMOTE_STAGING_DIR_CANDIDATES:
        writable, why = _remote_dir_writable(server_ip, d)
        if not writable:
            log(f"[STAGING] skip {d}: not writable ({why})")
            continue
        avail_kb = _remote_available_kb(server_ip, d)
        if avail_kb is None:
            log(f"[STAGING] skip {d}: cannot read free space (df failed)")
            continue
        if avail_kb < need_kb:
            log(f"[STAGING] skip {d}: insufficient space (need~{need_kb}KB avail={avail_kb}KB)")
            continue
        if avail_kb > best_avail_kb:
            best_dir = d
            best_avail_kb = avail_kb

    if best_dir:
        if best_dir == "/tmp":
            log("[STAGING] [WARN] selected /tmp as staging dir; this is on rootfs on many servers.")
        log(f"[STAGING] selected remote staging dir: {best_dir} (avail={best_avail_kb}KB)")
        return f"{best_dir}/ragflowauth_release_{tag}.tar"

    raise RuntimeError(
        "No suitable remote staging directory found (disk full or not writable). "
        "Try freeing space on the server or ensure /var/lib/docker or /mnt/replica is mounted."
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
    tmp_dir = Path(tempfile.mkdtemp(prefix="ragflowauth_release_"))
    tar_local = tmp_dir / f"ragflowauth_release_{tag}.tar"
    ok, out = _run_local(f'docker save {backend_image} {frontend_image} -o "{tar_local}"', timeout_s=7200)
    if not ok or not tar_local.exists():
        log(f"[ERROR] docker save failed:\n{out}")
        return finish(False, before, None)

    tar_size = int(tar_local.stat().st_size)
    log(f"[STAGING] local tar size: {tar_size} bytes")

    # Pick a remote staging location with enough free space.
    tar_on_test = _pick_remote_tar_path(test_ip, tar_size_bytes=tar_size, tag=tag, log=log)
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
    _ssh(test_ip, f"rm -f {tar_on_test} 2>/dev/null || true", timeout_s=60)

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
    try:
        tmp_dir.rmdir()
    except Exception:
        pass
    return finish(True, before, after)
