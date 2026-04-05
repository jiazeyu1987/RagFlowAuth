from __future__ import annotations

from typing import Callable

from tool.maintenance.features.onlyoffice_deploy_deploy_ops import (
    build_backend_context as _build_backend_context_impl,
    deploy_onlyoffice_container as _deploy_onlyoffice_container_impl,
    ensure_onlyoffice_network as _ensure_onlyoffice_network_impl,
    recreate_backend_container as _recreate_backend_container_impl,
)
from tool.maintenance.features.onlyoffice_deploy_models import (
    DeployOnlyOfficePipelineArtifacts,
)
from tool.maintenance.features.onlyoffice_deploy_postcheck_ops import (
    run_health_checks as _run_health_checks_impl,
)
from tool.maintenance.features.onlyoffice_deploy_precheck_ops import (
    check_or_pull_local_image as _check_or_pull_local_image_impl,
    export_local_image_tar as _export_local_image_tar_impl,
)
from tool.maintenance.features.onlyoffice_deploy_transfer_ops import (
    transfer_and_load_image as _transfer_and_load_image_impl,
)


def run_deploy_onlyoffice_pipeline(
    *,
    server_ip: str,
    server_user: str,
    image: str,
    onlyoffice_container: str,
    onlyoffice_port: int,
    backend_container: str,
    backend_port: int,
    log,
    artifacts: DeployOnlyOfficePipelineArtifacts,
    run_local_fn: Callable[[list[str], int], tuple[bool, str]],
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
    docker_inspect_fn: Callable[[str], dict | None],
    extract_env_map_fn: Callable[[dict], dict[str, str]],
    build_recreate_with_env_fn: Callable[[str, dict, str, dict[str, str]], str],
    wait_http_ok_fn: Callable[[str, int, int], tuple[bool, str]],
    staging_manager_cls,
    make_temp_dir_fn,
) -> bool:
    log(f"TARGET={server_user}@{server_ip}")
    log(f"ONLYOFFICE_IMAGE={image}")

    if not _check_or_pull_local_image_impl(image=image, log=log, run_local_fn=run_local_fn):
        return False

    ok, tar_size = _export_local_image_tar_impl(
        image=image,
        artifacts=artifacts,
        log=log,
        run_local_fn=run_local_fn,
        make_temp_dir_fn=make_temp_dir_fn,
    )
    if not ok:
        return False

    if not _transfer_and_load_image_impl(
        server_ip=server_ip,
        server_user=server_user,
        tar_size=tar_size,
        artifacts=artifacts,
        log=log,
        run_local_fn=run_local_fn,
        ssh_cmd_fn=ssh_cmd_fn,
        quote_part_fn=quote_part_fn,
        staging_manager_cls=staging_manager_cls,
    ):
        return False

    log("[6/8] Deploy onlyoffice container")
    _ensure_onlyoffice_network_impl(ssh_cmd_fn=ssh_cmd_fn)

    backend_ctx = _build_backend_context_impl(
        server_ip=server_ip,
        onlyoffice_port=onlyoffice_port,
        backend_port=backend_port,
        backend_container=backend_container,
        log=log,
        docker_inspect_fn=docker_inspect_fn,
        extract_env_map_fn=extract_env_map_fn,
    )
    if backend_ctx is None:
        return False

    if not _deploy_onlyoffice_container_impl(
        image=image,
        onlyoffice_container=onlyoffice_container,
        onlyoffice_port=onlyoffice_port,
        backend_ctx=backend_ctx,
        log=log,
        ssh_cmd_fn=ssh_cmd_fn,
        quote_part_fn=quote_part_fn,
    ):
        return False

    if not _recreate_backend_container_impl(
        backend_container=backend_container,
        backend_ctx=backend_ctx,
        log=log,
        ssh_cmd_fn=ssh_cmd_fn,
        quote_part_fn=quote_part_fn,
        build_recreate_with_env_fn=build_recreate_with_env_fn,
    ):
        return False

    if not _run_health_checks_impl(
        backend_port=backend_port,
        onlyoffice_port=onlyoffice_port,
        backend_container=backend_container,
        onlyoffice_container=onlyoffice_container,
        log=log,
        wait_http_ok_fn=wait_http_ok_fn,
        ssh_cmd_fn=ssh_cmd_fn,
        quote_part_fn=quote_part_fn,
    ):
        return False

    log("Deploy ONLYOFFICE completed")
    return True


def cleanup_deploy_onlyoffice_artifacts(
    *,
    artifacts: DeployOnlyOfficePipelineArtifacts,
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
    cleanup_dir_fn,
) -> None:
    if artifacts.tar_remote:
        try:
            ssh_cmd_fn(f"rm -f {quote_part_fn(artifacts.tar_remote)} 2>/dev/null || true", 30)
        except Exception:
            pass

    if artifacts.tar_local is not None:
        try:
            artifacts.tar_local.unlink(missing_ok=True)
        except Exception:
            pass

    if artifacts.tmp_dir is not None:
        cleanup_dir_fn(artifacts.tmp_dir)
