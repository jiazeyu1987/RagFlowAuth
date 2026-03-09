from __future__ import annotations

from typing import Any, Callable


def run_publish_flow(
    *,
    test_ip: str,
    prod_ip: str,
    app_dir: str,
    healthcheck_url: str,
    tag: str,
    test_version: Any,
    ragflow_images: list[str],
    log,
    docker_label_fn: Callable[[str, str, str], str],
    docker_inspect_fn: Callable[[str, str], dict | None],
    run_image_transfer_pipeline_fn,
    recreate_server_containers_from_inspect_fn,
    bootstrap_server_containers_fn,
    get_server_version_info_fn,
    default_server_user: str,
    default_staging_dir: str,
    staging_manager_cls,
    ssh_cmd_fn,
    run_local_fn: Callable[[list[str]], tuple[bool, str]],
) -> tuple[bool, Any | None]:
    if test_version.compose_path:
        log(f"Detected TEST compose: {test_version.compose_path}")
        log(f"Detected TEST env: {test_version.env_path or '(missing)'}")
    else:
        config_files = docker_label_fn(test_ip, "ragflowauth-backend", "com.docker.compose.project.config_files")
        working_dir = docker_label_fn(test_ip, "ragflowauth-backend", "com.docker.compose.project.working_dir")
        log("[WARN] docker-compose file not found on TEST; will publish by recreating PROD containers from inspect (docker run mode).")
        log(f"compose label config_files: {config_files or '(empty)'}")
        log(f"compose label working_dir: {working_dir or '(empty)'}")

    ok, out = run_image_transfer_pipeline_fn(
        test_ip=test_ip,
        prod_ip=prod_ip,
        app_dir=app_dir,
        tag=tag,
        backend_image=test_version.backend_image,
        frontend_image=test_version.frontend_image,
        ragflow_images=ragflow_images,
        default_server_user=default_server_user,
        default_staging_dir=default_staging_dir,
        log=log,
        staging_manager_cls=staging_manager_cls,
        ssh_cmd=ssh_cmd_fn,
        run_local=run_local_fn,
    )
    if not ok:
        log(f"[ERROR] {out}")
        return False, None

    log("[5/6] Recreate PROD containers with TEST images")
    prod_backend = docker_inspect_fn(prod_ip, "ragflowauth-backend")
    prod_frontend = docker_inspect_fn(prod_ip, "ragflowauth-frontend")
    if not prod_backend or not prod_frontend:
        log("[WARN] PROD containers not found (ragflowauth-backend/frontend); falling back to bootstrap mode.")
        ok2, msg2 = bootstrap_server_containers_fn(
            server_ip=prod_ip,
            backend_image=test_version.backend_image,
            frontend_image=test_version.frontend_image,
            healthcheck_url=healthcheck_url,
            log=log,
            app_dir=app_dir,
        )
        if not ok2:
            log(f"[ERROR] bootstrap failed: {msg2}")
            return False, None

        version_after = get_server_version_info_fn(server_ip=prod_ip, app_dir=app_dir)
        log("Publish completed (bootstrap mode)")
        return True, version_after

    ok, out = recreate_server_containers_from_inspect_fn(
        server_ip=prod_ip,
        backend_image=test_version.backend_image,
        frontend_image=test_version.frontend_image,
        healthcheck_url=healthcheck_url,
        log=log,
    )
    if not ok:
        log(f"[ERROR] {out}")
        return False, None

    version_after = get_server_version_info_fn(server_ip=prod_ip, app_dir=app_dir)
    log("Publish completed")
    return True, version_after
