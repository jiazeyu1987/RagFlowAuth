from __future__ import annotations

import secrets
from typing import Callable

from tool.maintenance.features.onlyoffice_deploy_models import DeployOnlyOfficeBackendContext


def ensure_onlyoffice_network(*, ssh_cmd_fn: Callable[[str, int], tuple[bool, str]]) -> None:
    ssh_cmd_fn(
        "docker network inspect ragflowauth-network >/dev/null 2>&1 || docker network create ragflowauth-network",
        60,
    )


def build_backend_context(
    *,
    server_ip: str,
    onlyoffice_port: int,
    backend_port: int,
    backend_container: str,
    log,
    docker_inspect_fn: Callable[[str], dict | None],
    extract_env_map_fn: Callable[[dict], dict[str, str]],
) -> DeployOnlyOfficeBackendContext | None:
    backend_inspect = docker_inspect_fn(backend_container)
    if not backend_inspect:
        log(f"[ERROR] backend container not found: {backend_container}")
        return None
    backend_image = str(((backend_inspect.get("Config") or {}).get("Image") or "")).strip()
    if not backend_image:
        log(f"[ERROR] unable to detect backend image from container: {backend_container}")
        return None

    env_map = extract_env_map_fn(backend_inspect)
    onlyoffice_jwt_secret = (env_map.get("ONLYOFFICE_JWT_SECRET") or "").strip() or secrets.token_hex(24)
    file_token_secret = (
        (env_map.get("ONLYOFFICE_FILE_TOKEN_SECRET") or "").strip()
        or (env_map.get("JWT_SECRET_KEY") or "").strip()
        or secrets.token_hex(24)
    )
    return DeployOnlyOfficeBackendContext(
        backend_inspect=backend_inspect,
        backend_image=backend_image,
        onlyoffice_jwt_secret=onlyoffice_jwt_secret,
        file_token_secret=file_token_secret,
        onlyoffice_server_url=f"http://{server_ip}:{int(onlyoffice_port)}",
        onlyoffice_api_base=f"http://{server_ip}:{int(backend_port)}",
    )


def deploy_onlyoffice_container(
    *,
    image: str,
    onlyoffice_container: str,
    onlyoffice_port: int,
    backend_ctx: DeployOnlyOfficeBackendContext,
    log,
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
) -> bool:
    rm_onlyoffice = f"docker rm -f {quote_part_fn(onlyoffice_container)} 2>/dev/null || true"
    onlyoffice_run_parts = [
        "docker",
        "run",
        "-d",
        "--name",
        onlyoffice_container,
        "--network",
        "ragflowauth-network",
        "-p",
        f"{int(onlyoffice_port)}:80",
        "-e",
        "JWT_ENABLED=true",
        "-e",
        f"JWT_SECRET={backend_ctx.onlyoffice_jwt_secret}",
        "-v",
        "onlyoffice_data:/var/www/onlyoffice/Data",
        "-v",
        "onlyoffice_logs:/var/log/onlyoffice",
        "-v",
        "onlyoffice_lib:/var/lib/onlyoffice",
        "--restart",
        "unless-stopped",
        image,
    ]
    run_onlyoffice = " ".join(quote_part_fn(part) for part in onlyoffice_run_parts)
    ok, out = ssh_cmd_fn(f"{rm_onlyoffice}; {run_onlyoffice}", 1200)
    if not ok:
        log(f"[ERROR] start onlyoffice failed:\n{out}")
        return False
    return True


def recreate_backend_container(
    *,
    backend_container: str,
    backend_ctx: DeployOnlyOfficeBackendContext,
    log,
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
    build_recreate_with_env_fn: Callable[[str, dict, str, dict[str, str]], str],
) -> bool:
    log("[7/8] Recreate backend container with ONLYOFFICE env")
    backend_network = str(((backend_ctx.backend_inspect.get("HostConfig") or {}).get("NetworkMode") or "")).strip()
    if backend_network and backend_network not in ("default", "bridge", "host", "none"):
        ok, out = ssh_cmd_fn(
            f"docker network inspect {quote_part_fn(backend_network)} >/dev/null 2>&1 || "
            f"docker network create {quote_part_fn(backend_network)}",
            60,
        )
        if not ok:
            log(f"[ERROR] ensure backend network failed:\n{out}")
            return False

    backend_env_overrides = {
        "ONLYOFFICE_ENABLED": "true",
        "ONLYOFFICE_SERVER_URL": backend_ctx.onlyoffice_server_url,
        "ONLYOFFICE_PUBLIC_API_BASE_URL": backend_ctx.onlyoffice_api_base,
        "ONLYOFFICE_JWT_SECRET": backend_ctx.onlyoffice_jwt_secret,
        "ONLYOFFICE_FILE_TOKEN_SECRET": backend_ctx.file_token_secret,
    }
    run_backend = build_recreate_with_env_fn(
        backend_container,
        backend_ctx.backend_inspect,
        backend_ctx.backend_image,
        backend_env_overrides,
    )
    ok, out = ssh_cmd_fn(
        f"docker stop {quote_part_fn(backend_container)} 2>/dev/null || true; "
        f"docker rm -f {quote_part_fn(backend_container)} 2>/dev/null || true; "
        f"{run_backend}",
        900,
    )
    if not ok:
        log(f"[ERROR] recreate backend failed:\n{out}")
        return False
    return True
