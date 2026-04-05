from __future__ import annotations

import time
from dataclasses import dataclass

from tool.maintenance.core.constants import DEFAULT_SERVER_USER
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.core.ssh_executor import SSHExecutor
from tool.maintenance.core.tempdir import cleanup_dir, make_temp_dir
from tool.maintenance.features.onlyoffice_deploy_pipeline_ops import (
    DeployOnlyOfficePipelineArtifacts,
    cleanup_deploy_onlyoffice_artifacts as _cleanup_deploy_onlyoffice_artifacts_impl,
    run_deploy_onlyoffice_pipeline as _run_deploy_onlyoffice_pipeline_impl,
)
from tool.maintenance.features.onlyoffice_deploy_runtime_ops import (
    build_recreate_from_inspect_with_env as _build_recreate_from_inspect_with_env_impl,
    docker_inspect as _docker_inspect_impl,
    extract_env_map as _extract_env_map_impl,
    quote_part as _quote_part_impl,
    sh_single_quote as _sh_single_quote_impl,
    wait_http_ok as _wait_http_ok_impl,
)
from tool.maintenance.features.release_exec_ops import run_local as _run_local_impl

DEFAULT_ONLYOFFICE_IMAGE = "onlyoffice/documentserver:latest"
DEFAULT_ONLYOFFICE_CONTAINER = "onlyoffice"
DEFAULT_ONLYOFFICE_PORT = 8082
DEFAULT_BACKEND_CONTAINER = "ragflowauth-backend"
DEFAULT_BACKEND_PORT = 8001


@dataclass(frozen=True)
class DeployOnlyOfficeResult:
    ok: bool
    log: str


def _run_local(argv: list[str], *, timeout_s: int = 3600) -> tuple[bool, str]:
    return _run_local_impl(argv, timeout_s=timeout_s)


def _sh_single_quote(value: str) -> str:
    return _sh_single_quote_impl(value)


def _quote_part(value: str) -> str:
    return _quote_part_impl(value, sh_single_quote_fn=_sh_single_quote)


def _ssh(ssh: SSHExecutor, command: str, *, timeout_s: int = 900) -> tuple[bool, str]:
    ok, out = ssh.execute(command, timeout_seconds=timeout_s)
    return ok, (out or "").strip()


def _docker_inspect(ssh: SSHExecutor, container_name: str) -> dict | None:
    return _docker_inspect_impl(ssh_exec=lambda cmd, timeout_s: _ssh(ssh, cmd, timeout_s=timeout_s), container_name=container_name)


def _extract_env_map(inspect: dict) -> dict[str, str]:
    return _extract_env_map_impl(inspect)


def _build_recreate_from_inspect_with_env(
    *,
    container_name: str,
    inspect: dict,
    new_image: str,
    env_overrides: dict[str, str],
) -> str:
    return _build_recreate_from_inspect_with_env_impl(
        container_name=container_name,
        inspect=inspect,
        new_image=new_image,
        env_overrides=env_overrides,
        extract_env_map_fn=_extract_env_map,
        quote_part_fn=_quote_part,
    )


def _wait_http_ok(
    *,
    ssh: SSHExecutor,
    url: str,
    timeout_s: int,
    interval_s: int = 3,
) -> tuple[bool, str]:
    return _wait_http_ok_impl(
        ssh_exec=lambda cmd, timeout_s: _ssh(ssh, cmd, timeout_s=timeout_s),
        url=url,
        timeout_s=timeout_s,
        interval_s=interval_s,
        quote_part_fn=_quote_part,
    )


def deploy_onlyoffice_from_local(
    *,
    server_ip: str,
    server_user: str = DEFAULT_SERVER_USER,
    image: str = DEFAULT_ONLYOFFICE_IMAGE,
    onlyoffice_container: str = DEFAULT_ONLYOFFICE_CONTAINER,
    onlyoffice_port: int = DEFAULT_ONLYOFFICE_PORT,
    backend_container: str = DEFAULT_BACKEND_CONTAINER,
    backend_port: int = DEFAULT_BACKEND_PORT,
    ui_log=None,
) -> DeployOnlyOfficeResult:
    log_lines: list[str] = []
    artifacts = DeployOnlyOfficePipelineArtifacts()
    ssh = SSHExecutor(server_ip, server_user)

    def log(msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] {msg}"
        log_lines.append(line)
        if ui_log:
            try:
                ui_log(line)
            except Exception:
                pass

    def finish(ok: bool) -> DeployOnlyOfficeResult:
        return DeployOnlyOfficeResult(ok=ok, log="\n".join(log_lines))

    try:
        ok = _run_deploy_onlyoffice_pipeline_impl(
            server_ip=server_ip,
            server_user=server_user,
            image=image,
            onlyoffice_container=onlyoffice_container,
            onlyoffice_port=onlyoffice_port,
            backend_container=backend_container,
            backend_port=backend_port,
            log=log,
            artifacts=artifacts,
            run_local_fn=lambda argv, timeout_s: _run_local(argv, timeout_s=timeout_s),
            ssh_cmd_fn=lambda command, timeout_s: _ssh(ssh, command, timeout_s=timeout_s),
            quote_part_fn=_quote_part,
            docker_inspect_fn=lambda container_name: _docker_inspect(ssh, container_name),
            extract_env_map_fn=_extract_env_map,
            build_recreate_with_env_fn=lambda container_name, inspect, new_image, env_overrides: _build_recreate_from_inspect_with_env(
                container_name=container_name,
                inspect=inspect,
                new_image=new_image,
                env_overrides=env_overrides,
            ),
            wait_http_ok_fn=lambda url, timeout_s, interval_s: _wait_http_ok(
                ssh=ssh,
                url=url,
                timeout_s=timeout_s,
                interval_s=interval_s,
            ),
            staging_manager_cls=RemoteStagingManager,
            make_temp_dir_fn=make_temp_dir,
        )
        return finish(ok)
    except Exception as e:
        log(f"[ERROR] unexpected exception: {e}")
        return finish(False)
    finally:
        _cleanup_deploy_onlyoffice_artifacts_impl(
            artifacts=artifacts,
            ssh_cmd_fn=lambda command, timeout_s: _ssh(ssh, command, timeout_s=timeout_s),
            quote_part_fn=_quote_part,
            cleanup_dir_fn=cleanup_dir,
        )
