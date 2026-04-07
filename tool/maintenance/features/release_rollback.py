from __future__ import annotations

from dataclasses import dataclass

from tool.maintenance.core.constants import DEFAULT_SERVER_USER
from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.features import release_publish as rp


@dataclass(frozen=True)
class RollbackResult:
    ok: bool
    log: str


def feature_list_ragflowauth_versions(
    *,
    server_ip: str,
    server_user: str = DEFAULT_SERVER_USER,
    limit: int = 20,
) -> list[str]:
    """
    List candidate versions that exist on the target server.
    We consider a version valid if BOTH ragflowauth-backend and ragflowauth-frontend images with the same tag exist.
    """
    ssh = SSHExecutor(server_ip, server_user)
    ok1, out1 = ssh.execute("docker images ragflowauth-backend --format '{{.Tag}}' 2>/dev/null | head -n 200 || true")
    ok2, out2 = ssh.execute("docker images ragflowauth-frontend --format '{{.Tag}}' 2>/dev/null | head -n 200 || true")
    if not ok1 and not ok2:
        return []

    tags_backend = {t.strip() for t in (out1 or "").splitlines() if t.strip() and t.strip() != "<none>"}
    tags_frontend = {t.strip() for t in (out2 or "").splitlines() if t.strip() and t.strip() != "<none>"}
    tags = sorted(tags_backend & tags_frontend, reverse=True)
    return tags[: max(1, int(limit))]


def feature_rollback_ragflowauth_to_version(
    *,
    server_ip: str,
    version: str,
    server_user: str = DEFAULT_SERVER_USER,
) -> RollbackResult:
    """
    Rollback ragflowauth-backend/frontend containers on the target server to the specified image tags.

    Safety: requires existing containers so we can recreate with correct volumes/env/ports from inspect.
    """
    logs: list[str] = []

    def log(msg: str) -> None:
        logs.append(msg)

    version = (version or "").strip()
    if not version:
        return RollbackResult(ok=False, log="missing version")

    backend_image = f"ragflowauth-backend:{version}"
    frontend_image = f"ragflowauth-frontend:{version}"

    log(f"[ROLLBACK] server={server_ip} version={version}")

    backend_inspect = rp._docker_inspect(server_ip, "ragflowauth-backend")
    frontend_inspect = rp._docker_inspect(server_ip, "ragflowauth-frontend")
    if not backend_inspect or not frontend_inspect:
        log("[ROLLBACK] [ERROR] containers not found (ragflowauth-backend/frontend).")
        log("[ROLLBACK] Hint: use the publish flow to (re)deploy containers first.")
        return RollbackResult(ok=False, log="\n".join(logs))

    network_name = (
        (backend_inspect.get("HostConfig") or {}).get("NetworkMode")
        or (frontend_inspect.get("HostConfig") or {}).get("NetworkMode")
        or "bridge"
    )
    ok, out = rp._ensure_network(server_ip, network_name)
    if not ok:
        log(f"[ROLLBACK] [ERROR] ensure network failed: {out}")
        return RollbackResult(ok=False, log="\n".join(logs))

    log("[ROLLBACK] stopping/removing old containers")
    rp._ssh_cmd(server_ip, "docker stop ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")
    rp._ssh_cmd(server_ip, "docker rm -f ragflowauth-backend ragflowauth-frontend 2>/dev/null || true")

    run_frontend = rp._build_recreate_from_inspect("ragflowauth-frontend", frontend_inspect, new_image=frontend_image)
    run_backend = rp._build_recreate_from_inspect("ragflowauth-backend", backend_inspect, new_image=backend_image)
    log(f"[ROLLBACK] run frontend: {run_frontend}")
    okf, outf = rp._ssh_cmd(server_ip, run_frontend)
    if not okf:
        log(f"[ROLLBACK] [ERROR] frontend recreate failed: {outf}")
        return RollbackResult(ok=False, log="\n".join(logs))

    log(f"[ROLLBACK] run backend: {run_backend}")
    okb, outb = rp._ssh_cmd(server_ip, run_backend)
    if not okb:
        log(f"[ROLLBACK] [ERROR] backend recreate failed: {outb}")
        return RollbackResult(ok=False, log="\n".join(logs))

    ok, out = rp._wait_prod_ready(prod_ip=server_ip, healthcheck_url="http://127.0.0.1:8001/health")
    if not ok:
        log("[ROLLBACK] [ERROR] healthcheck failed")
        log(out)
        return RollbackResult(ok=False, log="\n".join(logs))

    log("[ROLLBACK] completed")
    return RollbackResult(ok=True, log="\n".join(logs))

