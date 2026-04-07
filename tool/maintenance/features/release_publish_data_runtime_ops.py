from __future__ import annotations

import time
from typing import Callable


def ssh_must(*, ssh_fn: Callable[[str, str], tuple[bool, str]], ip: str, cmd: str, log, hint: str) -> str | None:
    ok, out = ssh_fn(ip, cmd)
    if ok:
        return out
    log(f"[ERROR] {hint}: {out}")
    return None


def docker_container_status_and_ip(
    *, ssh_fn: Callable[[str, str], tuple[bool, str]], ip: str, container_name: str
) -> tuple[bool, str, str]:
    cmd = (
        "set -e; "
        f"docker inspect -f '{{{{.State.Status}}}}' {container_name} 2>/dev/null || echo ''; "
        f"docker inspect -f '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_name} 2>/dev/null || echo ''"
    )
    ok, out = ssh_fn(ip, cmd)
    if not ok:
        return False, "", ""
    lines = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return True, (lines[0] if lines else ""), ""
    return True, lines[-2], lines[-1]


def ensure_firewalld_allows_ragflow_bridge(*, ssh_fn: Callable[[str, str], tuple[bool, str]], ip: str, log) -> None:
    """
    CentOS/RHEL hosts sometimes have a leftover `inet firewalld` nft table even when firewalld is failing.

    If the docker bridge interface for `ragflow_compose_ragflow` isn't listed in firewalld zone chains,
    traffic between containers can be rejected/blocked (symptoms: ragflow-cpu cannot reach es01:9200).

    We add a narrow accept rule for intra-bridge forwarding on that docker bridge interface.
    """
    ok, net_id = ssh_fn(ip, "docker network inspect ragflow_compose_ragflow --format '{{.Id}}' 2>/dev/null || echo ''")
    net_id = (net_id or "").strip().splitlines()[-1].strip() if (net_id or "").strip() else ""
    if not ok or not net_id:
        log("[PROD] [WARN] unable to read ragflow_compose_ragflow network id; skipping firewall workaround")
        return

    bridge = f"br-{net_id[:12]}"
    log(f"[PROD] ragflow docker bridge: {bridge}")

    ok, out = ssh_fn(ip, "nft list table inet firewalld >/dev/null 2>&1 && echo HAS_FIREWALLD || echo NO_FIREWALLD")
    if not ok:
        log("[PROD] [WARN] unable to detect nft firewalld table; skipping firewall workaround")
        return
    if "NO_FIREWALLD" in (out or ""):
        return

    rule_pat = f"iifname {bridge} oifname {bridge} accept"
    ok, out = ssh_fn(ip, "nft list chain inet firewalld filter_FORWARD 2>/dev/null || echo ''")
    if ok and rule_pat in (out or ""):
        return

    log(f"[PROD] [WARN] adding nft rule to allow intra-bridge forwarding: {rule_pat}")
    ssh_fn(ip, f"nft insert rule inet firewalld filter_FORWARD iifname {bridge} oifname {bridge} accept 2>/dev/null || true")


def wait_for_container_running(
    *,
    docker_container_status_and_ip_fn: Callable[[str, str], tuple[bool, str, str]],
    ip: str,
    container_name: str,
    seconds: int,
    log,
    step: str,
) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        ok, status, ipaddr = docker_container_status_and_ip_fn(ip, container_name)
        if ok and status == "running":
            log(f"{step} {container_name}: running ip={ipaddr or '(empty)'}")
            return True
        time.sleep(3)
    ok, status, ipaddr = docker_container_status_and_ip_fn(ip, container_name)
    log(f"{step} {container_name}: not running status={status or '(missing)'} ip={ipaddr or '(empty)'}")
    return False


def ensure_ragflow_running_on_prod(
    *,
    ssh_fn: Callable[[str, str], tuple[bool, str]],
    ssh_must_fn,
    ensure_firewalld_allows_ragflow_bridge_fn,
    wait_for_container_running_fn,
    docker_container_status_and_ip_fn,
    prod_ip: str,
    app_dir: str,
    log,
) -> bool:
    compose_dir = f"{app_dir}/ragflow_compose"

    # Start the whole stack (best-effort errors should be visible).
    ensure_firewalld_allows_ragflow_bridge_fn(prod_ip, log=log)
    out = ssh_must_fn(
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
    wait_for_container_running_fn(prod_ip, "ragflow_compose-es01-1", seconds=120, log=log, step="[PROD] wait")
    wait_for_container_running_fn(prod_ip, "ragflow_compose-mysql-1", seconds=120, log=log, step="[PROD] wait")
    wait_for_container_running_fn(prod_ip, "ragflow_compose-redis-1", seconds=120, log=log, step="[PROD] wait")
    wait_for_container_running_fn(prod_ip, "ragflow_compose-minio-1", seconds=120, log=log, step="[PROD] wait")

    # Known failure mode: ragflow-cpu exists but has no network IP / endpoint or exits immediately.
    ok, status, ipaddr = docker_container_status_and_ip_fn(prod_ip, "ragflow_compose-ragflow-cpu-1")
    if not ok:
        log("[PROD] [WARN] unable to inspect ragflow-cpu container; continuing")
        return True

    status2, ipaddr2 = status, ipaddr

    if status2 != "running" or not ipaddr2:
        log(f"[PROD] [WARN] ragflow-cpu unhealthy: status={status2 or '(missing)'} ip={ipaddr2 or '(empty)'}")
        log("[PROD] Attempting to force-recreate ragflow-cpu (common fix for missing network endpoint)")
        out = ssh_must_fn(
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
        ok2, status2, ipaddr2 = docker_container_status_and_ip_fn(prod_ip, "ragflow_compose-ragflow-cpu-1")
        log(f"[PROD] ragflow-cpu after recreate: status={status2 or '(missing)'} ip={ipaddr2 or '(empty)'}")

    if status2 != "running" or not ipaddr2:
        log("[PROD] [ERROR] ragflow-cpu still not healthy after compose start")
        ok3, ps_out = ssh_fn(prod_ip, "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' | sed -n '1,120p' 2>&1 || true")
        if ok3 and ps_out.strip():
            log(f"[PROD] docker ps -a (top):\n{ps_out.strip()}")
        ok4, logs_out = ssh_fn(prod_ip, "docker logs --tail 200 ragflow_compose-ragflow-cpu-1 2>&1 || true")
        if ok4 and logs_out.strip():
            log(f"[PROD] ragflow-cpu logs (tail):\n{logs_out.strip()}")
        return False

    # Stability check: sometimes the container starts and then exits quickly (e.g. due to transient ES connectivity).
    log("[PROD] wait 15s and re-check ragflow-cpu stability")
    time.sleep(15)
    ok_st, st_status, st_ip = docker_container_status_and_ip_fn(prod_ip, "ragflow_compose-ragflow-cpu-1")
    if ok_st and (st_status != "running" or not st_ip):
        log(f"[PROD] [WARN] ragflow-cpu became unhealthy after start: status={st_status or '(missing)'} ip={st_ip or '(empty)'}")
        log("[PROD] Retrying one more force-recreate ragflow-cpu")
        out = ssh_must_fn(
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
        ok2b, st2_status, st2_ip = docker_container_status_and_ip_fn(prod_ip, "ragflow_compose-ragflow-cpu-1")
        log(f"[PROD] ragflow-cpu after retry: status={st2_status or '(missing)'} ip={st2_ip or '(empty)'}")
        if not ok2b or st2_status != "running" or not st2_ip:
            log("[PROD] [ERROR] ragflow-cpu still unstable after retry")
            return False

    # Sanity: if curl exists, check host endpoint (non-fatal if curl missing).
    ok5, curl_out = ssh_fn(
        prod_ip,
        "command -v curl >/dev/null 2>&1 && (curl -fsS http://127.0.0.1:80/ >/dev/null && echo RAGFLOW_OK || echo RAGFLOW_FAIL) || echo NO_CURL",
    )
    if ok5 and curl_out.strip():
        log(f"[PROD] ragflow http check: {curl_out.strip().splitlines()[-1]}")
    return True


def ensure_ragflowauth_running_on_prod(*, ssh_fn: Callable[[str, str], tuple[bool, str]], prod_ip: str, log) -> bool:
    # Don't recreate containers here; data publish assumes images already exist on PROD.
    ok, out = ssh_fn(
        prod_ip,
        "docker start ragflowauth-backend ragflowauth-frontend 2>/dev/null || true; "
        "docker ps --format '{{.Names}}\\t{{.Status}}' | grep -E '^ragflowauth-(backend|frontend)\\b' || true",
    )
    if not ok:
        log(f"[PROD] [ERROR] failed to start ragflowauth containers: {out}")
        return False
    if out.strip():
        log(f"[PROD] ragflowauth containers:\n{out.strip()}")

    # Healthcheck with retries (backend may need a few seconds to become ready).
    ok, out = ssh_fn(prod_ip, "command -v curl >/dev/null 2>&1 && echo HAS_CURL || echo NO_CURL")
    has_curl = ok and (out or "").strip().endswith("HAS_CURL")
    if not has_curl:
        log("[PROD] backend healthcheck: NO_CURL (skipped)")
        return True

    last: str = ""
    deadline = time.time() + 90
    while time.time() < deadline:
        ok, out = ssh_fn(
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
    ok2, ps_out = ssh_fn(prod_ip, "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' | grep -E '^ragflowauth-' 2>&1 || true")
    if ok2 and ps_out.strip():
        log(f"[PROD] docker ps -a ragflowauth:\n{ps_out.strip()}")
    ok3, logs_out = ssh_fn(prod_ip, "docker logs --tail 200 ragflowauth-backend 2>&1 || true")
    if ok3 and logs_out.strip():
        log(f"[PROD] ragflowauth-backend logs (tail):\n{logs_out.strip()}")
    return False
