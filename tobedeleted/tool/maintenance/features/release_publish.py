from __future__ import annotations

import time
from dataclasses import dataclass

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.features.release_exec_ops import run_local as _run_local_impl
from tool.maintenance.features.release_exec_ops import ssh_cmd as _ssh_cmd_impl
from tool.maintenance.features.release_publish_flow_ops import run_publish_flow
from tool.maintenance.features.release_publish_probe_ops import (
    detect_ragflow_images_on_server as _detect_ragflow_images_on_server_impl,
    docker_inspect as _docker_inspect_impl,
    preflight_check_ragflow_base_url as _preflight_check_ragflow_base_url_impl,
    read_ragflow_base_url as _read_ragflow_base_url_impl,
)
from tool.maintenance.features.release_publish_runtime_ops import (
    bootstrap_server_containers_impl as _bootstrap_server_containers_impl,
    build_recreate_from_inspect as _build_recreate_from_inspect_impl,
    ensure_network as _ensure_network_impl,
    recreate_server_containers_from_inspect_impl as _recreate_server_containers_from_inspect_impl,
    sh_single_quote as _sh_single_quote_impl,
    wait_server_ready as _wait_server_ready_impl,
)
from tool.maintenance.features.release_publish_transfer_ops import run_image_transfer_pipeline
from tool.maintenance.features.release_publish_version_ops import (
    detect_compose_and_env_paths as _detect_compose_and_env_paths_impl,
    docker_container_image as _docker_container_image_impl,
    docker_label as _docker_label_impl,
    get_server_version_info_impl as _get_server_version_info_impl,
    sha256_of_remote_file as _sha256_of_remote_file_impl,
)


DEFAULT_REMOTE_APP_DIR = "/opt/ragflowauth"
DEFAULT_REMOTE_STAGING_DIR = "/var/lib/docker/tmp"


@dataclass(frozen=True)
class ServerVersionInfo:
    server_ip: str
    backend_image: str
    frontend_image: str
    compose_path: str
    env_path: str
    compose_sha256: str
    env_sha256: str


@dataclass(frozen=True)
class PublishResult:
    ok: bool
    log: str
    version_before: ServerVersionInfo | None
    version_after: ServerVersionInfo | None


def _run_local(argv: list[str], *, timeout_s: int = 3600) -> tuple[bool, str]:
    return _run_local_impl(argv, timeout_s=timeout_s)


def _ssh_cmd(ip: str, command: str) -> tuple[bool, str]:
    return _ssh_cmd_impl(ip=ip, user=DEFAULT_SERVER_USER, command=command, timeout_seconds=900)


def _read_ragflow_base_url(*, server_ip: str, app_dir: str) -> tuple[bool, str]:
    return _read_ragflow_base_url_impl(ssh_cmd=_ssh_cmd, server_ip=server_ip, app_dir=app_dir)


def preflight_check_ragflow_base_url(
    *,
    server_ip: str,
    expected_server_ip: str,
    app_dir: str,
    log,
    role_name: str,
) -> bool:
    return _preflight_check_ragflow_base_url_impl(
        read_base_url_fn=lambda server_ip, app_dir: _read_ragflow_base_url(server_ip=server_ip, app_dir=app_dir),
        server_ip=server_ip,
        expected_server_ip=expected_server_ip,
        app_dir=app_dir,
        log=log,
        role_name=role_name,
    )
def docker_load_tar_on_server(*, server_ip: str, tar_path: str) -> tuple[bool, str]:
    """Load a docker image tarball on a remote server."""
    return _ssh_cmd(server_ip, f"docker load -i {tar_path}")


def _docker_label(ip: str, container_name: str, label: str) -> str:
    return _docker_label_impl(ssh_cmd=_ssh_cmd, ip=ip, container_name=container_name, label=label)

def _detect_compose_and_env_paths(ip: str, *, app_dir: str) -> tuple[str, str]:
    return _detect_compose_and_env_paths_impl(
        ssh_cmd=_ssh_cmd,
        docker_label_fn=lambda ip_, container, label: _docker_label(ip_, container, label),
        ip=ip,
        app_dir=app_dir,
    )


def _sh_single_quote(value: str) -> str:
    return _sh_single_quote_impl(value)


def _docker_inspect(ip: str, container_name: str) -> dict | None:
    return _docker_inspect_impl(ssh_cmd=_ssh_cmd, ip=ip, container_name=container_name)


def _detect_ragflow_images_on_server(*, server_ip: str) -> list[str]:
    return _detect_ragflow_images_on_server_impl(ssh_cmd=_ssh_cmd, server_ip=server_ip)


def _ensure_network(ip: str, network_name: str) -> tuple[bool, str]:
    return _ensure_network_impl(ssh_cmd=_ssh_cmd, ip=ip, network_name=network_name)


def _build_recreate_from_inspect(container_name: str, inspect: dict, *, new_image: str) -> str:
    return _build_recreate_from_inspect_impl(
        container_name,
        inspect,
        new_image=new_image,
        sh_single_quote_fn=_sh_single_quote,
    )


def _wait_prod_ready(
    *,
    prod_ip: str,
    healthcheck_url: str,
    backend_container: str = "ragflowauth-backend",
    timeout_s: int = 90,
) -> tuple[bool, str]:
    return _wait_server_ready_impl(
        ssh_cmd=_ssh_cmd,
        prod_ip=prod_ip,
        healthcheck_url=healthcheck_url,
        backend_container=backend_container,
        timeout_s=timeout_s,
    )


def _sha256_of_remote_file(ip: str, path: str) -> str:
    return _sha256_of_remote_file_impl(ssh_cmd=_ssh_cmd, ip=ip, path=path)


def _docker_container_image(ip: str, container_name: str) -> str:
    return _docker_container_image_impl(ssh_cmd=_ssh_cmd, ip=ip, container_name=container_name)


def get_server_version_info(*, server_ip: str, app_dir: str = DEFAULT_REMOTE_APP_DIR) -> ServerVersionInfo:
    return _get_server_version_info_impl(
        server_ip=server_ip,
        app_dir=app_dir,
        docker_container_image_fn=lambda ip, container: _docker_container_image(ip, container),
        detect_compose_and_env_paths_fn=lambda ip, app_dir_: _detect_compose_and_env_paths(ip, app_dir=app_dir_),
        sha256_of_remote_file_fn=lambda ip, path: _sha256_of_remote_file(ip, path),
        version_info_factory=ServerVersionInfo,
    )


def publish_from_test_to_prod(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    prod_ip: str = PROD_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    healthcheck_url: str = "http://127.0.0.1:8001/health",
    include_ragflow_images: bool = False,
) -> PublishResult:
    """
    Publish the currently-running TEST containers to PROD by:
    1) On TEST: docker save the exact images used by ragflowauth-backend/frontend
    2) scp -3: copy tar + docker-compose.yml + .env from TEST to PROD
    3) On PROD: backup existing compose/.env, docker load, replace compose/.env, restart compose

    Notes:
    - Runs from the local Windows machine (uses local ssh/scp).
    - Requires key-based SSH access to both servers.
    """
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_lines.append(f"[{ts}] {msg}")

    version_before = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    test_version = get_server_version_info(server_ip=test_ip, app_dir=app_dir)
    if not test_version.backend_image or not test_version.frontend_image:
        return PublishResult(
            ok=False,
            log="\n".join(log_lines + [f"[ERROR] unable to detect test images: {test_version}"]),
            version_before=version_before,
            version_after=None,
        )
    tag = (version or time.strftime("%Y%m%d_%H%M%S", time.localtime())).strip()
    log(f"TEST={test_ip} PROD={prod_ip} VERSION={tag}")
    log(f"Detected TEST images: backend={test_version.backend_image} frontend={test_version.frontend_image}")
    ragflow_images: list[str] = []
    if include_ragflow_images:
        ragflow_images = _detect_ragflow_images_on_server(server_ip=test_ip)
        if ragflow_images:
            log(f"Detected TEST RAGFlow images: {', '.join(ragflow_images)}")
        else:
            log("[WARN] include_ragflow_images enabled but no RAGFlow images detected on TEST.")

    # Safety checks: ensure each environment points to its own RAGFlow.
    if not preflight_check_ragflow_base_url(
        server_ip=test_ip,
        expected_server_ip=test_ip,
        app_dir=app_dir,
        log=log,
        role_name="TEST",
    ):
        log("[ERROR] Preflight check failed; refusing to publish (TEST base_url mismatch).")
        return PublishResult(False, "\n".join(log_lines), version_before, None)
    if not preflight_check_ragflow_base_url(
        server_ip=prod_ip,
        expected_server_ip=prod_ip,
        app_dir=app_dir,
        log=log,
        role_name="PROD",
    ):
        log("[ERROR] Preflight check failed; refusing to publish (PROD base_url mismatch).")
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    ok, version_after = run_publish_flow(
        test_ip=test_ip,
        prod_ip=prod_ip,
        app_dir=app_dir,
        healthcheck_url=healthcheck_url,
        tag=tag,
        test_version=test_version,
        ragflow_images=ragflow_images,
        log=log,
        docker_label_fn=lambda ip, container, label: _docker_label(ip, container, label),
        docker_inspect_fn=lambda ip, container: _docker_inspect(ip, container),
        run_image_transfer_pipeline_fn=run_image_transfer_pipeline,
        recreate_server_containers_from_inspect_fn=recreate_server_containers_from_inspect,
        bootstrap_server_containers_fn=bootstrap_server_containers,
        get_server_version_info_fn=get_server_version_info,
        default_server_user=DEFAULT_SERVER_USER,
        default_staging_dir=DEFAULT_REMOTE_STAGING_DIR,
        staging_manager_cls=RemoteStagingManager,
        ssh_cmd_fn=_ssh_cmd,
        run_local_fn=lambda argv: _run_local(argv, timeout_s=7200),
    )
    if not ok:
        return PublishResult(False, "\n".join(log_lines), version_before, None)

    return PublishResult(True, "\n".join(log_lines), version_before, version_after)


def recreate_server_containers_from_inspect(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
) -> tuple[bool, str]:
    return _recreate_server_containers_from_inspect_impl(
        server_ip=server_ip,
        backend_image=backend_image,
        frontend_image=frontend_image,
        healthcheck_url=healthcheck_url,
        log=log,
        docker_inspect_fn=_docker_inspect,
        ssh_cmd=_ssh_cmd,
        ensure_network_fn=_ensure_network,
        build_recreate_fn=_build_recreate_from_inspect,
        wait_ready_fn=_wait_prod_ready,
    )


def bootstrap_server_containers(
    *,
    server_ip: str,
    backend_image: str,
    frontend_image: str,
    healthcheck_url: str,
    log,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    network_name: str = "ragflowauth-network",
    frontend_port: int = 3001,
    backend_port: int = 8001,
) -> tuple[bool, str]:
    return _bootstrap_server_containers_impl(
        server_ip=server_ip,
        backend_image=backend_image,
        frontend_image=frontend_image,
        healthcheck_url=healthcheck_url,
        log=log,
        ssh_cmd=_ssh_cmd,
        ensure_network_fn=_ensure_network,
        wait_ready_fn=_wait_prod_ready,
        app_dir=app_dir,
        network_name=network_name,
        frontend_port=frontend_port,
        backend_port=backend_port,
    )
