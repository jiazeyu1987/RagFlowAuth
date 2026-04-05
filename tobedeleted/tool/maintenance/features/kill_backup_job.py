from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.ssh_executor import SSHExecutor


@dataclass(frozen=True)
class KillBackupJobResult:
    ok: bool
    log: str


_KILL_CODE = r"""
import json
import time

from backend.services.data_security_store import DataSecurityStore

store = DataSecurityStore()
job_id = store.get_active_job_id()
res = {"active_job_id": job_id, "action": "none"}

if job_id is None:
    print(json.dumps(res, ensure_ascii=False))
    raise SystemExit(0)

try:
    store.request_cancel_job(int(job_id), reason="maintenance_tool_force_kill")
    store.update_job(
        int(job_id),
        status="failed",
        progress=100,
        message="force_killed",
        detail="force killed by maintenance tool",
        finished_at_ms=int(time.time() * 1000),
    )
    try:
        store.release_backup_lock()
    except Exception:
        pass
    res["action"] = "cancel_requested_and_mark_failed"
except Exception as e:
    res["action"] = "error"
    res["error"] = str(e)

print(json.dumps(res, ensure_ascii=False))
"""


def kill_running_backup_job(*, server_ip: str, server_user: str = "root") -> KillBackupJobResult:
    """
    Force-stop the currently running/queued DataSecurity backup job on the target server.

    Strategy (best-effort):
    1) Inside ragflowauth-backend container, mark active job as canceling/failed + release sqlite lock.
    2) Restart ragflowauth-backend container to terminate the running backup thread/process.

    Notes:
    - This is destructive (will interrupt an in-progress backup).
    - Only touches ragflowauth-backend; does NOT restart ragflow/ragflowauth-frontend/other containers.
    """
    ssh = SSHExecutor(server_ip, server_user)
    logs: list[str] = [f"[TARGET] {server_user}@{server_ip}"]

    def run(cmd: str, *, timeout: int = 120, stdin: str | None = None) -> tuple[bool, str]:
        ok, out = ssh.execute(cmd, timeout_seconds=timeout, stdin_data=stdin)
        logs.append(f"$ {cmd}\n{(out or '').strip()}\n")
        return ok, out or ""

    ok = True

    # Ensure backend container exists.
    _, out = run("docker ps -a --format '{{.Names}}' 2>/dev/null || true", timeout=30)
    names = [line.strip() for line in (out or "").splitlines() if line.strip()]
    if "ragflowauth-backend" not in names:
        logs.append("[ERROR] ragflowauth-backend container not found; cannot stop backup job.")
        return KillBackupJobResult(ok=False, log="\n".join(logs).strip() + "\n")

    # Attempt cooperative cancel + mark failed + release lock.
    ok1, out1 = run("docker exec -i ragflowauth-backend python -", timeout=60, stdin=_KILL_CODE.strip() + "\n")
    ok = ok and ok1

    # Restart backend container to actually terminate the running backup thread.
    logs.append("[ACTION] docker restart ragflowauth-backend (terminate backup thread)")
    ok2, _ = run("docker restart ragflowauth-backend 2>&1 || true", timeout=120)
    ok = ok and ok2

    # Verify no active job visible (best-effort).
    verify_code = r"""
import json
from backend.services.data_security_store import DataSecurityStore
store = DataSecurityStore()
print(json.dumps({"active_job_id": store.get_active_job_id()}, ensure_ascii=False))
"""
    ok3, _ = run("docker exec -i ragflowauth-backend python -", timeout=60, stdin=verify_code.strip() + "\n")
    ok = ok and ok3

    return KillBackupJobResult(ok=bool(ok), log="\n".join(logs).strip() + "\n")

