from __future__ import annotations

from typing import Callable


def run_health_checks(
    *,
    backend_port: int,
    onlyoffice_port: int,
    backend_container: str,
    onlyoffice_container: str,
    log,
    wait_http_ok_fn: Callable[[str, int, int], tuple[bool, str]],
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
) -> bool:
    log("[8/8] Health checks")
    ok, out = wait_http_ok_fn(f"http://127.0.0.1:{int(backend_port)}/health", 120, 3)
    if not ok:
        log(f"[ERROR] backend health check failed: {out}")
        _, diag = ssh_cmd_fn(f"docker logs --tail 150 {quote_part_fn(backend_container)} 2>&1 || true", 60)
        if diag:
            log(f"[DIAG] backend logs:\n{diag}")
        return False

    ok, out = wait_http_ok_fn(f"http://127.0.0.1:{int(onlyoffice_port)}/healthcheck", 300, 3)
    if not ok:
        log(f"[ERROR] onlyoffice health check failed: {out}")
        _, diag = ssh_cmd_fn(f"docker logs --tail 150 {quote_part_fn(onlyoffice_container)} 2>&1 || true", 60)
        if diag:
            log(f"[DIAG] onlyoffice logs:\n{diag}")
        return False
    return True
