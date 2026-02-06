from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.core.service_controller import ServiceController
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.features.release_publish import DEFAULT_REMOTE_APP_DIR, PublishResult, ServerVersionInfo, get_server_version_info


def _run_local(argv: list[str], *, timeout_s: int = 7200) -> tuple[bool, str]:
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    out = "\n".join(
        line for line in out.splitlines() if not line.startswith("close - IO is still pending on closed socket.")
    ).strip()
    return proc.returncode == 0, out


def _ssh(ip: str, command: str) -> tuple[bool, str]:
    ssh = SSHExecutor(ip, DEFAULT_SERVER_USER)
    return ssh.execute(command, timeout_seconds=1800)


def _read_base_url(ip: str, *, app_dir: str) -> tuple[bool, str]:
    cfg_path = f"{app_dir}/ragflow_config.json"
    cmd = (
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = _ssh(ip, cmd)
    text = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if not ok or not text or text == "MISSING":
        return False, out.strip() if out else f"missing/invalid {cfg_path}"
    return True, text


def _ensure_prod_base_url(prod_ip: str, *, app_dir: str, desired: str, log) -> bool:
    ok, current = _read_base_url(prod_ip, app_dir=app_dir)
    if not ok:
        log(f"[PRECHECK] [ERROR] unable to read PROD base_url: {current}")
        return False

    current = current.strip()
    log(f"[PRECHECK] PROD current base_url: {current}")
    if desired in current:
        return True

    cfg_path = f"{app_dir}/ragflow_config.json"
    log(f"[PRECHECK] Fix PROD base_url -> {desired}")
    fix_cmd = (
        f"set -e; "
        f"cp -f {cfg_path} {cfg_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; "
        f"tmp=$(mktemp); "
        f"sed -E 's#(\"base_url\"[[:space:]]*:[[:space:]]*\")([^\\\"]+)(\")#\\1{desired}\\3#' {cfg_path} > $tmp; "
        f"mv -f $tmp {cfg_path}; "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = _ssh(prod_ip, fix_cmd)
    new_val = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if not ok or desired not in new_val:
        log(f"[PRECHECK] [ERROR] failed to update PROD base_url. out={out}")
        return False
    log(f"[PRECHECK] PROD base_url updated: {new_val}")
    return True


def _stop_services_and_verify(
    ip: str,
    *,
    app_dir: str,
    log,
    who: str,
    timeout_s: int = 60,
) -> bool:
    controller = ServiceController(exec_fn=lambda cmd, t: _ssh(ip, cmd), log=lambda m: log(m))
    res = controller.stop_and_verify(app_dir=app_dir, mode="down", timeout_s=timeout_s, who=who)
    return bool(res.ok)


def _ssh_must(ip: str, cmd: str, *, log, hint: str) -> str | None:
    ok, out = _ssh(ip, cmd)
    if ok:
        return out
    log(f"[ERROR] {hint}: {out}")
    return None


def _docker_container_status_and_ip(ip: str, container_name: str) -> tuple[bool, str, str]:
    cmd = (
        "set -e; "
        f"docker inspect -f '{{{{.State.Status}}}}' {container_name} 2>/dev/null || echo ''; "
        f"docker inspect -f '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_name} 2>/dev/null || echo ''"
    )
    ok, out = _ssh(ip, cmd)
    if not ok:
        return False, "", ""
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return True, (lines[0] if lines else ""), ""
    return True, lines[-2], lines[-1]


def _ensure_firewalld_allows_ragflow_bridge(ip: str, *, log) -> None:
    """
    CentOS/RHEL hosts sometimes have a leftover `inet firewalld` nft table even when firewalld is failing.

    If the docker bridge interface for `ragflow_compose_ragflow` isn't listed in firewalld zone chains,
    traffic between containers can be rejected/blocked (symptoms: ragflow-cpu cannot reach es01:9200).

    We add a narrow accept rule for intra-bridge forwarding on that docker bridge interface.
    """
    ok, net_id = _ssh(ip, "docker network inspect ragflow_compose_ragflow --format '{{.Id}}' 2>/dev/null || echo ''")
    net_id = (net_id or "").strip().splitlines()[-1].strip() if (net_id or "").strip() else ""
    if not ok or not net_id:
        log("[PROD] [WARN] unable to read ragflow_compose_ragflow network id; skipping firewall workaround")
        return

    bridge = f"br-{net_id[:12]}"
    log(f"[PROD] ragflow docker bridge: {bridge}")

    ok, out = _ssh(ip, "nft list table inet firewalld >/dev/null 2>&1 && echo HAS_FIREWALLD || echo NO_FIREWALLD")
    if not ok:
        log("[PROD] [WARN] unable to detect nft firewalld table; skipping firewall workaround")
        return
    if "NO_FIREWALLD" in (out or ""):
        return

    rule_pat = f"iifname {bridge} oifname {bridge} accept"
    ok, out = _ssh(ip, "nft list chain inet firewalld filter_FORWARD 2>/dev/null || echo ''")
    if ok and rule_pat in (out or ""):
        return

    log(f"[PROD] [WARN] adding nft rule to allow intra-bridge forwarding: {rule_pat}")
    _ssh(ip, f"nft insert rule inet firewalld filter_FORWARD iifname {bridge} oifname {bridge} accept 2>/dev/null || true")


def _wait_for_container_running(ip: str, container_name: str, *, seconds: int, log, step: str) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        ok, status, ipaddr = _docker_container_status_and_ip(ip, container_name)
        if ok and status == "running":
            log(f"{step} {container_name}: running ip={ipaddr or '(empty)'}")
            return True
        time.sleep(3)
    ok, status, ipaddr = _docker_container_status_and_ip(ip, container_name)
    log(f"{step} {container_name}: not running status={status or '(missing)'} ip={ipaddr or '(empty)'}")
    return False


def _ensure_ragflow_running_on_prod(prod_ip: str, *, app_dir: str, log) -> bool:
    compose_dir = f"{app_dir}/ragflow_compose"

    # Start the whole stack (best-effort errors should be visible).
    _ensure_firewalld_allows_ragflow_bridge(prod_ip, log=log)
    out = _ssh_must(
        prod_ip,
        f"set -e; cd {compose_dir} && docker compose up -d 2>&1",
        log=log,
        hint="docker compose up -d on PROD failed",
    )
    if out is None:
        return False
    if out.strip():
        log(f"[PROD] compose up output:\n{out.strip()}")

    # Wait for core dependencies + ragflow.
    _wait_for_container_running(prod_ip, "ragflow_compose-es01-1", seconds=120, log=log, step="[PROD] wait")
    _wait_for_container_running(prod_ip, "ragflow_compose-mysql-1", seconds=120, log=log, step="[PROD] wait")
    _wait_for_container_running(prod_ip, "ragflow_compose-redis-1", seconds=120, log=log, step="[PROD] wait")
    _wait_for_container_running(prod_ip, "ragflow_compose-minio-1", seconds=120, log=log, step="[PROD] wait")

    # Known failure mode: ragflow-cpu exists but has no network IP / endpoint or exits immediately.
    ok, status, ipaddr = _docker_container_status_and_ip(prod_ip, "ragflow_compose-ragflow-cpu-1")
    if not ok:
        log("[PROD] [WARN] unable to inspect ragflow-cpu container; continuing")
        return True

    status2, ipaddr2 = status, ipaddr

    if status2 != "running" or not ipaddr2:
        log(f"[PROD] [WARN] ragflow-cpu unhealthy: status={status2 or '(missing)'} ip={ipaddr2 or '(empty)'}")
        log("[PROD] Attempting to force-recreate ragflow-cpu (common fix for missing network endpoint)")
        out = _ssh_must(
            prod_ip,
            f"set -e; cd {compose_dir} && docker compose up -d --force-recreate ragflow-cpu 2>&1",
            log=log,
            hint="force-recreate ragflow-cpu failed",
        )
        if out is None:
            return False
        if out.strip():
            log(f"[PROD] force-recreate output:\n{out.strip()}")

        # Re-check ragflow-cpu health.
        ok2, status2, ipaddr2 = _docker_container_status_and_ip(prod_ip, "ragflow_compose-ragflow-cpu-1")
        log(f"[PROD] ragflow-cpu after recreate: status={status2 or '(missing)'} ip={ipaddr2 or '(empty)'}")

    if status2 != "running" or not ipaddr2:
        log("[PROD] [ERROR] ragflow-cpu still not healthy after compose start")
        ok3, ps_out = _ssh(prod_ip, "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' | sed -n '1,120p' 2>&1 || true")
        if ok3 and ps_out.strip():
            log(f"[PROD] docker ps -a (top):\n{ps_out.strip()}")
        ok4, logs_out = _ssh(prod_ip, "docker logs --tail 200 ragflow_compose-ragflow-cpu-1 2>&1 || true")
        if ok4 and logs_out.strip():
            log(f"[PROD] ragflow-cpu logs (tail):\n{logs_out.strip()}")
        return False

    # Stability check: sometimes the container starts and then exits quickly (e.g. due to transient ES connectivity).
    log("[PROD] wait 15s and re-check ragflow-cpu stability")
    time.sleep(15)
    ok_st, st_status, st_ip = _docker_container_status_and_ip(prod_ip, "ragflow_compose-ragflow-cpu-1")
    if ok_st and (st_status != "running" or not st_ip):
        log(f"[PROD] [WARN] ragflow-cpu became unhealthy after start: status={st_status or '(missing)'} ip={st_ip or '(empty)'}")
        log("[PROD] Retrying one more force-recreate ragflow-cpu")
        out = _ssh_must(
            prod_ip,
            f"set -e; cd {compose_dir} && docker compose up -d --force-recreate ragflow-cpu 2>&1",
            log=log,
            hint="second force-recreate ragflow-cpu failed",
        )
        if out is None:
            return False
        if out.strip():
            log(f"[PROD] second force-recreate output:\n{out.strip()}")
        time.sleep(10)
        ok2b, st2_status, st2_ip = _docker_container_status_and_ip(prod_ip, "ragflow_compose-ragflow-cpu-1")
        log(f"[PROD] ragflow-cpu after retry: status={st2_status or '(missing)'} ip={st2_ip or '(empty)'}")
        if not ok2b or st2_status != "running" or not st2_ip:
            log("[PROD] [ERROR] ragflow-cpu still unstable after retry")
            return False

    # Sanity: if curl exists, check host endpoint (non-fatal if curl missing).
    ok5, curl_out = _ssh(
        prod_ip,
        "command -v curl >/dev/null 2>&1 && (curl -fsS http://127.0.0.1:80/ >/dev/null && echo RAGFLOW_OK || echo RAGFLOW_FAIL) || echo NO_CURL",
    )
    if ok5 and curl_out.strip():
        log(f"[PROD] ragflow http check: {curl_out.strip().splitlines()[-1]}")
    return True


def _ensure_ragflowauth_running_on_prod(prod_ip: str, *, log) -> bool:
    # Don't recreate containers here; data publish assumes images already exist on PROD.
    ok, out = _ssh(prod_ip, "docker start ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; docker ps --format '{{.Names}}\\t{{.Status}}' | grep -E '^ragflowauth-(backend|frontend)\\b' || true")
    if not ok:
        log(f"[PROD] [ERROR] failed to start ragflowauth containers: {out}")
        return False
    if out.strip():
        log(f"[PROD] ragflowauth containers:\n{out.strip()}")

    # Healthcheck with retries (backend may need a few seconds to become ready).
    ok, out = _ssh(prod_ip, "command -v curl >/dev/null 2>&1 && echo HAS_CURL || echo NO_CURL")
    has_curl = ok and (out or "").strip().endswith("HAS_CURL")
    if not has_curl:
        log("[PROD] backend healthcheck: NO_CURL (skipped)")
        return True

    last: str = ""
    deadline = time.time() + 90
    while time.time() < deadline:
        ok, out = _ssh(
            prod_ip,
            "curl -fsS http://127.0.0.1:8001/health >/dev/null && echo BACKEND_OK || echo BACKEND_FAIL",
        )
        last = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else "BACKEND_FAIL"
        if ok and last == "BACKEND_OK":
            log("[PROD] backend healthcheck: BACKEND_OK")
            return True
        time.sleep(3)

    # Still failing: capture actionable diagnostics and fail publish.
    log(f"[PROD] [ERROR] backend healthcheck failed after retries: {last}")
    ok2, ps_out = _ssh(prod_ip, "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' | grep -E '^ragflowauth-' 2>&1 || true")
    if ok2 and ps_out.strip():
        log(f"[PROD] docker ps -a ragflowauth:\n{ps_out.strip()}")
    ok3, logs_out = _ssh(prod_ip, "docker logs --tail 200 ragflowauth-backend 2>&1 || true")
    if ok3 and logs_out.strip():
        log(f"[PROD] ragflowauth-backend logs (tail):\n{logs_out.strip()}")
    return False


def publish_data_from_test_to_prod(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    prod_ip: str = PROD_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    ragflow_port: int = 9380,
    log_cb: Callable[[str], None] | None = None,
) -> PublishResult:
    """
    Publish TEST *data* -> PROD:
    - auth.db
    - ragflow_compose_* docker volumes (RAGFlow data)

    This is destructive to PROD data; caller must do double confirmation in UI.
    """
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        if log_cb is not None:
            try:
                log_cb(line)
            except Exception:
                # Never let UI logging crash the publish flow.
                pass

    def finish(ok: bool, before: ServerVersionInfo | None, after: ServerVersionInfo | None) -> PublishResult:
        return PublishResult(ok=ok, log="\n".join(log_lines), version_before=before, version_after=after)

    before = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    tag = (version or time.strftime("%Y%m%d_%H%M%S", time.localtime())).strip()

    log(f"DATA TEST={test_ip} -> PROD={prod_ip} VERSION={tag}")

    ok, test_base = _read_base_url(test_ip, app_dir=app_dir)
    if not ok:
        log(f"[PRECHECK] [ERROR] unable to read TEST base_url: {test_base}")
        return finish(False, before, None)
    log(f"[PRECHECK] TEST base_url: {test_base}")
    if (TEST_SERVER_IP not in test_base) and ("localhost" not in test_base) and ("127.0.0.1" not in test_base):
        log(f"[PRECHECK] [ERROR] TEST base_url mismatch; refusing to publish data.")
        return finish(False, before, None)

    desired_prod = f"http://{PROD_SERVER_IP}:{ragflow_port}"
    if not _ensure_prod_base_url(prod_ip, app_dir=app_dir, desired=desired_prod, log=log):
        log("[PRECHECK] [ERROR] unable to ensure PROD base_url; refusing to publish data.")
        return finish(False, before, None)

    staging_test = RemoteStagingManager(exec_fn=lambda c: _ssh(test_ip, c), log=log)
    staging_prod = RemoteStagingManager(exec_fn=lambda c: _ssh(prod_ip, c), log=log)

    workdir_test: str | None = None
    tar_test: str | None = None
    workdir_prod: str | None = None
    tar_prod: str | None = None

    def cleanup_best_effort() -> None:
        # Only cleanup our temporary artifacts (NEVER touch backups or /opt/ragflowauth/data/backups).
        staging_test.cleanup_legacy_tmp_release_files()
        staging_prod.cleanup_legacy_tmp_release_files()
        _ssh(test_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        _ssh(prod_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        if tar_test:
            staging_test.cleanup_path(tar_test)
        if workdir_test:
            _ssh(test_ip, f"rm -rf {workdir_test} 2>/dev/null || true")
        if tar_prod:
            staging_prod.cleanup_path(tar_prod)
        if workdir_prod:
            _ssh(prod_ip, f"rm -rf {workdir_prod} 2>/dev/null || true")

    try:
        log("[PRECHECK] Clean legacy tmp artifacts (best-effort)")
        staging_test.cleanup_legacy_tmp_release_files()
        staging_prod.cleanup_legacy_tmp_release_files()
        _ssh(test_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        _ssh(prod_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")

        # Pick staging dirs on both servers to avoid filling rootfs (/tmp is often on /).
        pick_test = staging_test.pick_best_dir()
        pick_prod = staging_prod.pick_best_dir()

        workdir_test = RemoteStagingManager.join(pick_test.dir, f"ragflowauth_data_release_{tag}")
        tar_test = RemoteStagingManager.join(pick_test.dir, f"ragflowauth_data_release_{tag}.tar.gz")
        workdir_prod = RemoteStagingManager.join(pick_prod.dir, f"ragflowauth_data_release_{tag}")
        tar_prod = RemoteStagingManager.join(pick_prod.dir, f"ragflowauth_data_release_{tag}.tar.gz")

        log("[1/7] Prepare pack dir on TEST")
        ok, out = _ssh(test_ip, f"rm -rf {workdir_test} {tar_test}; mkdir -p {workdir_test}/volumes && echo OK")
        if not ok:
            log(f"[ERROR] TEST prepare failed: {out}")
            return finish(False, before, None)

        log("[2/7] Stop services on TEST (for consistent snapshot)")
        if not _stop_services_and_verify(test_ip, app_dir=app_dir, log=log, who="TEST"):
            log("[ERROR] TEST services did not stop cleanly; aborting to avoid inconsistent snapshot")
            return finish(False, before, None)

        log("[3/7] Export auth.db + ragflow volumes on TEST")
        ok, out = _ssh(
            test_ip,
            f"cp -f {app_dir}/data/auth.db {workdir_test}/auth.db 2>/dev/null || true; ls -lh {workdir_test}/auth.db 2>&1 || true",
        )
        if not ok:
            log(f"[ERROR] copy auth.db on TEST failed: {out}")
            return finish(False, before, None)

        export_cmd = r"""
set -e
mkdir -p "{workdir}/volumes"
docker image inspect alpine >/dev/null 2>&1 || docker pull alpine:latest >/dev/null 2>&1 || true
vols=$(docker volume ls --format '{{{{.Name}}}}' | grep '^ragflow_compose_' || true)
if [ -z "$vols" ]; then
  echo "NO_VOLUMES"
  exit 0
fi
for v in $vols; do
  echo "EXPORT $v"
  docker run --rm -v "$v:/data:ro" -v "{workdir}/volumes:/backup" alpine sh -lc "cd /data && tar -czf /backup/${{v}}.tar.gz ."
done
""".strip().format(workdir=workdir_test)
        ok, out = _ssh(test_ip, export_cmd)
        if not ok:
            log(f"[ERROR] export volumes on TEST failed:\n{out}")
            return finish(False, before, None)
        if out.strip():
            log(out.strip())

        log("[4/7] Pack data tar on TEST")
        ok, out = _ssh(test_ip, f"tar -czf {tar_test} -C {workdir_test} auth.db volumes && ls -lh {tar_test} 2>&1 || true")
        if not ok:
            log(f"[ERROR] tar pack on TEST failed: {out}")
            return finish(False, before, None)

        # Free TEST workdir ASAP (tar already created).
        _ssh(test_ip, f"rm -rf {workdir_test} 2>/dev/null || true")
        workdir_test = None

        log("[5/7] Transfer data tar TEST -> PROD (scp -3)")
        scp_cmd = [
            "scp",
            "-3",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{DEFAULT_SERVER_USER}@{test_ip}:{tar_test}",
            f"{DEFAULT_SERVER_USER}@{prod_ip}:{tar_prod}",
        ]
        ok, out = _run_local(
            scp_cmd,
            timeout_s=7200,
        )
        if not ok:
            log(f"[ERROR] scp -3 failed: {out}")
            return finish(False, before, None)

        # Remove TEST tar after transfer succeeds.
        staging_test.cleanup_path(tar_test)
        tar_test = None

        log("[6/7] Apply on PROD (stop, backup, restore)")

        # Stop services (strict)
        if not _stop_services_and_verify(prod_ip, app_dir=app_dir, log=log, who="PROD"):
            log("[ERROR] PROD services did not stop cleanly; aborting to avoid partial restore")
            return finish(False, before, None)

        # Backup current db (best-effort)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        _ssh(
            prod_ip,
            f"mkdir -p /tmp/restore_backup_{ts} >/dev/null 2>&1 || true; "
            f"cp -f {app_dir}/data/auth.db /tmp/restore_backup_{ts}/auth.db 2>/dev/null || true",
        )

        ok, out = _ssh(
            prod_ip,
            f"rm -rf {workdir_prod}; mkdir -p {workdir_prod} && tar -xzf {tar_prod} -C {workdir_prod} && echo OK",
        )
        if not ok:
            log(f"[ERROR] extract on PROD failed: {out}")
            return finish(False, before, None)

        # Remove PROD tar after extraction succeeds.
        staging_prod.cleanup_path(tar_prod)
        tar_prod = None

        # Restore auth.db
        ok, out = _ssh(prod_ip, f"cp -f {workdir_prod}/auth.db {app_dir}/data/auth.db && echo OK")
        if not ok:
            log(f"[ERROR] restore auth.db on PROD failed: {out}")
            return finish(False, before, None)

        # Restore volumes
        restore_vol_cmd = r"""
set -e
if [ ! -d "{workdir}/volumes" ]; then
  echo "NO_VOLUMES_DIR"
  exit 0
fi
files=$(ls -1 "{workdir}/volumes"/*.tar.gz 2>/dev/null || true)
if [ -z "$files" ]; then
  echo "NO_VOLUME_TARS"
  exit 0
fi
for f in $files; do
  name=$(basename "$f" .tar.gz)
  echo "RESTORE $name"
  docker volume inspect "$name" >/dev/null 2>&1 || docker volume create "$name" >/dev/null
  docker run --rm -v "$name:/data" -v "{workdir}/volumes:/backup:ro" alpine sh -lc "rm -rf /data/* /data/.[!.]* /data/..?* 2>/dev/null || true; tar -xzf /backup/${{name}}.tar.gz -C /data"
done
""".strip().format(workdir=workdir_prod)
        ok, out = _ssh(prod_ip, restore_vol_cmd)
        if not ok:
            log(f"[ERROR] restore volumes on PROD failed:\n{out}")
            return finish(False, before, None)
        if out.strip():
            log(out.strip())

        log("[7/8] Restart services on PROD")
        if not _ensure_ragflow_running_on_prod(prod_ip, app_dir=app_dir, log=log):
            log("[ERROR] PROD ragflow services did not start cleanly; aborting")
            return finish(False, before, None)

        if not _ensure_ragflowauth_running_on_prod(prod_ip, log=log):
            log("[ERROR] PROD ragflowauth services did not start cleanly; aborting")
            return finish(False, before, None)

        log("[8/8] Cleanup temporary artifacts on PROD")
        _ssh(prod_ip, f"rm -rf {workdir_prod} 2>/dev/null || true")
        workdir_prod = None

        after = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
        log("Publish data completed")
        return finish(True, before, after)
    finally:
        cleanup_best_effort()
