def upload_auth_db_to_test(*, auth_db, ssh_exec, subprocess_mod, test_server_ip, time_mod, ui_log):
    # 2) Backup current auth.db (best-effort) then upload auth.db
    ui_log("[SYNC] [2/5] Upload auth.db to TEST")
    ts = time_mod.strftime("%Y%m%d_%H%M%S", time_mod.localtime())
    ssh_exec(
        f"mkdir -p /tmp/restore_backup_{ts} >/dev/null 2>&1 || true; "
        f"cp -f /opt/ragflowauth/data/auth.db /tmp/restore_backup_{ts}/auth.db 2>/dev/null || true"
    )

    scp_cmd = [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        str(auth_db),
        f"root@{test_server_ip}:/opt/ragflowauth/data/auth.db",
    ]
    proc = subprocess_mod.run(scp_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"SCP auth.db 失败: {(proc.stderr or proc.stdout or '').strip()}")
    return ts
