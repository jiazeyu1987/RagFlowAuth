from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep

from tool.maintenance.core.ssh_executor import SSHExecutor


@dataclass(frozen=True)
class CancelBackupJobResult:
    ok: bool
    job_id: int | None
    status: str | None
    message: str
    final: bool
    waited_seconds: int
    raw: str


def cancel_active_backup_job(
    *,
    server_ip: str,
    server_user: str = "root",
    wait_seconds: int = 60,
    poll_interval_seconds: int = 2,
) -> CancelBackupJobResult:
    """
    Cancel the currently active (queued/running) backup job on the target server.

    This is implemented via SSH + `docker exec` (no HTTP auth dependency).
    """
    ssh = SSHExecutor(server_ip, server_user)
    wait_seconds = int(max(0, min(600, wait_seconds)))
    poll_interval_seconds = int(max(1, min(10, poll_interval_seconds)))

    script = r"""
import json
import time
from backend.services.data_security_store import DataSecurityStore

store = DataSecurityStore()
job_id = store.get_active_job_id()
if job_id is None:
    print(json.dumps({"ok": False, "job_id": None, "status": None, "message": "no_active_job"}))
else:
    job = store.request_cancel_job(int(job_id), reason="tool_cancel")
    print(json.dumps({"ok": True, "job_id": int(job.id), "status": job.status, "message": "cancel_requested"}))
""".lstrip()

    ok, out = ssh.execute("docker exec -i ragflowauth-backend python -", timeout_seconds=40, stdin_data=script)
    if not ok:
        return CancelBackupJobResult(
            ok=False,
            job_id=None,
            status=None,
            message="ssh_failed",
            final=False,
            waited_seconds=0,
            raw=out or "",
        )

    raw = out.strip()
    try:
        payload = json.loads(raw.splitlines()[-1])
        initial_ok = bool(payload.get("ok"))
        job_id = payload.get("job_id")
        status = payload.get("status")
        message = str(payload.get("message") or "")
        if not initial_ok or job_id is None:
            return CancelBackupJobResult(
                ok=initial_ok,
                job_id=job_id,
                status=status,
                message=message,
                final=False,
                waited_seconds=0,
                raw=raw,
            )
    except Exception:
        return CancelBackupJobResult(ok=False, job_id=None, status=None, message="parse_failed", final=False, waited_seconds=0, raw=raw)

    # Best-effort: wait for the worker to reach a terminal state so users can immediately retry.
    terminal = {"canceled", "failed", "completed"}
    waited = 0
    final_status = str(status or "")

    while waited < wait_seconds and final_status not in terminal:
        sleep(poll_interval_seconds)
        waited += poll_interval_seconds

        poll_script = rf"""
import json
from backend.services.data_security_store import DataSecurityStore

store = DataSecurityStore()
job = store.get_job({int(job_id)})
print(json.dumps({{"ok": True, "job_id": int(job.id), "status": job.status, "message": job.message or "", "progress": job.progress}}))
""".lstrip()

        ok2, out2 = ssh.execute("docker exec -i ragflowauth-backend python -", timeout_seconds=40, stdin_data=poll_script)
        if not ok2:
            break
        raw += "\n" + (out2 or "").strip()
        try:
            payload2 = json.loads((out2 or "").strip().splitlines()[-1])
            final_status = str(payload2.get("status") or "")
            message = str(payload2.get("message") or message)
        except Exception:
            break

    final = final_status in terminal
    # Add a small, human-friendly hint (without changing status).
    if final:
        message = message or "done"
    else:
        # Provide a timestamp so operators can correlate with server logs quickly.
        ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        message = message or f"still_canceling@{ts}"

    return CancelBackupJobResult(
        ok=True,
        job_id=int(job_id),
        status=final_status,
        message=message,
        final=final,
        waited_seconds=int(waited),
        raw=raw,
    )
