from __future__ import annotations

from typing import Callable


def read_base_url(*, ssh_fn: Callable[[str, str], tuple[bool, str]], ip: str, app_dir: str) -> tuple[bool, str]:
    cfg_path = f"{app_dir}/ragflow_config.json"
    cmd = (
        f"test -f {cfg_path} || (echo MISSING && exit 0); "
        f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
    )
    ok, out = ssh_fn(ip, cmd)
    text = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if not ok or not text or text == "MISSING":
        return False, out.strip() if out else f"missing/invalid {cfg_path}"
    return True, text


def ensure_prod_base_url(
    *,
    read_base_url_fn: Callable[[str, str], tuple[bool, str]],
    ssh_fn: Callable[[str, str], tuple[bool, str]],
    prod_ip: str,
    app_dir: str,
    desired: str,
    log,
) -> bool:
    ok, current = read_base_url_fn(prod_ip, app_dir)
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
    ok, out = ssh_fn(prod_ip, fix_cmd)
    new_val = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
    if not ok or desired not in new_val:
        log(f"[PRECHECK] [ERROR] failed to update PROD base_url. out={out}")
        return False
    log(f"[PRECHECK] PROD base_url updated: {new_val}")
    return True


def stop_services_and_verify(
    *,
    service_controller_cls,
    ssh_fn: Callable[[str, str], tuple[bool, str]],
    ip: str,
    app_dir: str,
    log,
    who: str,
    timeout_s: int = 60,
) -> bool:
    controller = service_controller_cls(exec_fn=lambda cmd, t: ssh_fn(ip, cmd), log=lambda m: log(m))
    res = controller.stop_and_verify(app_dir=app_dir, mode="down", timeout_s=timeout_s, who=who)
    return bool(res.ok)
