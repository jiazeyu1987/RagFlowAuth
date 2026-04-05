def restart_services_on_test(*, ssh_exec, ui_log):
    # 4) Restart services
    ui_log("[SYNC] [4/5] Restart services on TEST")
    ssh_exec("cd /opt/ragflowauth/ragflow_compose 2>/dev/null && docker compose up -d 2>&1 || true")
    ssh_exec("docker start ragflowauth-backend ragflowauth-frontend 2>&1 || true")


def healthcheck_backend_on_test(*, ssh_exec, ui_log):
    # 5) Healthcheck (best-effort)
    ui_log("[SYNC] [5/5] Healthcheck on TEST (best-effort)")
    okh, outh = ssh_exec(
        "command -v curl >/dev/null 2>&1 && "
        "(curl -fsS http://127.0.0.1:8001/health >/dev/null && echo BACKEND_OK || echo BACKEND_FAIL) || echo NO_CURL"
    )
    if okh and (outh or "").strip():
        ui_log(f"[SYNC] backend health: {(outh or '').strip().splitlines()[-1]}")
