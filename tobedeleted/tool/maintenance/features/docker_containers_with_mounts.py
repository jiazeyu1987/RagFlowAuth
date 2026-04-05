from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tool.maintenance.core.ssh_executor import SSHExecutor


@dataclass(frozen=True)
class ContainersWithMountsResult:
    text: str


def show_containers_with_mounts(*, ssh: SSHExecutor, log: Callable[[str, str], None]) -> ContainersWithMountsResult:
    log("[CONTAINER-CHECK] Step 1: docker ps", "INFO")
    ok, out = ssh.execute("docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'")
    if not ok:
        raise RuntimeError(f"获取容器列表失败：\n{out}")

    lines = [l for l in (out or "").splitlines() if l.strip()]
    containers: list[tuple[str, str, str]] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3:
            containers.append((parts[0], parts[1], parts[2]))

    # Best-effort: read replica_target_path from backend DB (used to validate the mount target path)
    replica_target_path = ""
    try:
        cfg_cmd = (
            "docker exec ragflowauth-backend python -c "
            "\"import sqlite3; conn = sqlite3.connect('/app/data/auth.db'); "
            "cur = conn.cursor(); cur.execute('SELECT replica_target_path FROM data_security_settings LIMIT 1'); "
            "row = cur.fetchone(); print(row[0] if row else 'NOT_SET'); conn.close()\""
        )
        ok2, cfg = ssh.execute(cfg_cmd)
        if ok2:
            replica_target_path = (cfg or "").strip()
    except Exception:
        replica_target_path = ""

    text = "=== 运行中的容器及挂载状态 ===\n\n"
    if replica_target_path:
        text += f"data_security_settings.replica_target_path: {replica_target_path}\n\n"
    text += f"{'容器名称':<30} {'挂载检查':<50} {'状态':<15}\n"
    text += "=" * 95 + "\n"

    for name, image, status in containers:
        # Check mounts for /mnt/replica
        inspect_cmd = f"docker inspect {name} --format '{{{{json .Mounts}}}}' 2>/dev/null || echo '[]'"
        ok3, mounts_json = ssh.execute(inspect_cmd)
        mount_ok = ok3 and "/mnt/replica" in (mounts_json or "")
        mount_info = "✓ 已挂载 /mnt/replica" if mount_ok else "✗ 未挂载 /mnt/replica"
        text += f"{name:<30} {mount_info:<50} {status[:15]:<15}\n"

    return ContainersWithMountsResult(text=text)
