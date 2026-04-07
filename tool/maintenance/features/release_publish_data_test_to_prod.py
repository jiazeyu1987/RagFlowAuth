from __future__ import annotations

import time
from typing import Callable

from tool.maintenance.core.constants import DEFAULT_SERVER_USER, PROD_SERVER_IP, TEST_SERVER_IP
from tool.maintenance.core.remote_staging import RemoteStagingManager
from tool.maintenance.core.service_controller import ServiceController
from tool.maintenance.features.release_exec_ops import run_local as _run_local_impl
from tool.maintenance.features.release_exec_ops import ssh_cmd as _ssh_cmd_impl
from tool.maintenance.features.release_publish_data_pipeline_ops import run_publish_data_pipeline
from tool.maintenance.features.release_publish_data_precheck_ops import (
    ensure_prod_base_url as _ensure_prod_base_url_impl,
    read_base_url as _read_base_url_impl,
    stop_services_and_verify as _stop_services_and_verify_impl,
)
from tool.maintenance.features.release_publish_data_runtime_ops import (
    docker_container_status_and_ip as _docker_container_status_and_ip_impl,
    ensure_firewalld_allows_ragflow_bridge as _ensure_firewalld_allows_ragflow_bridge_impl,
    ensure_ragflow_running_on_prod as _ensure_ragflow_running_on_prod_impl,
    ensure_ragflowauth_running_on_prod as _ensure_ragflowauth_running_on_prod_impl,
    ssh_must as _ssh_must_impl,
    wait_for_container_running as _wait_for_container_running_impl,
)
from tool.maintenance.features.release_publish import DEFAULT_REMOTE_APP_DIR, PublishResult, ServerVersionInfo, get_server_version_info


def _run_local(argv: list[str], *, timeout_s: int = 7200) -> tuple[bool, str]:
    return _run_local_impl(argv, timeout_s=timeout_s)


def _ssh(ip: str, command: str) -> tuple[bool, str]:
    return _ssh_cmd_impl(ip=ip, user=DEFAULT_SERVER_USER, command=command, timeout_seconds=1800)


def _read_base_url(ip: str, *, app_dir: str) -> tuple[bool, str]:
    return _read_base_url_impl(ssh_fn=_ssh, ip=ip, app_dir=app_dir)


def _ensure_prod_base_url(prod_ip: str, *, app_dir: str, desired: str, log) -> bool:
    return _ensure_prod_base_url_impl(
        read_base_url_fn=lambda ip, app_dir: _read_base_url(ip, app_dir=app_dir),
        ssh_fn=_ssh,
        prod_ip=prod_ip,
        app_dir=app_dir,
        desired=desired,
        log=log,
    )


def _stop_services_and_verify(
    ip: str,
    *,
    app_dir: str,
    log,
    who: str,
    timeout_s: int = 60,
) -> bool:
    return _stop_services_and_verify_impl(
        service_controller_cls=ServiceController,
        ssh_fn=_ssh,
        ip=ip,
        app_dir=app_dir,
        log=log,
        who=who,
        timeout_s=timeout_s,
    )


def _ssh_must(ip: str, cmd: str, *, log, hint: str) -> str | None:
    return _ssh_must_impl(ssh_fn=_ssh, ip=ip, cmd=cmd, log=log, hint=hint)


def _docker_container_status_and_ip(ip: str, container_name: str) -> tuple[bool, str, str]:
    return _docker_container_status_and_ip_impl(ssh_fn=_ssh, ip=ip, container_name=container_name)


def _ensure_firewalld_allows_ragflow_bridge(ip: str, *, log) -> None:
    return _ensure_firewalld_allows_ragflow_bridge_impl(ssh_fn=_ssh, ip=ip, log=log)


def _wait_for_container_running(ip: str, container_name: str, *, seconds: int, log, step: str) -> bool:
    return _wait_for_container_running_impl(
        docker_container_status_and_ip_fn=lambda ip_, name: _docker_container_status_and_ip(ip_, name),
        ip=ip,
        container_name=container_name,
        seconds=seconds,
        log=log,
        step=step,
    )


def _ensure_ragflow_running_on_prod(prod_ip: str, *, app_dir: str, log) -> bool:
    return _ensure_ragflow_running_on_prod_impl(
        ssh_fn=_ssh,
        ssh_must_fn=lambda ip, cmd, *, log, hint: _ssh_must(ip, cmd, log=log, hint=hint),
        ensure_firewalld_allows_ragflow_bridge_fn=lambda ip, *, log: _ensure_firewalld_allows_ragflow_bridge(ip, log=log),
        wait_for_container_running_fn=lambda ip, container_name, *, seconds, log, step: _wait_for_container_running(
            ip, container_name, seconds=seconds, log=log, step=step
        ),
        docker_container_status_and_ip_fn=lambda ip, name: _docker_container_status_and_ip(ip, name),
        prod_ip=prod_ip,
        app_dir=app_dir,
        log=log,
    )


def _ensure_ragflowauth_running_on_prod(prod_ip: str, *, log) -> bool:
    return _ensure_ragflowauth_running_on_prod_impl(ssh_fn=_ssh, prod_ip=prod_ip, log=log)


def publish_data_from_test_to_prod(
    *,
    version: str | None = None,
    test_ip: str = TEST_SERVER_IP,
    prod_ip: str = PROD_SERVER_IP,
    app_dir: str = DEFAULT_REMOTE_APP_DIR,
    ragflow_port: int = 9380,
    log_cb: Callable[[str], None] | None = None,
) -> PublishResult:
    """
    Publish TEST *data* -> PROD:
    - auth.db
    - ragflow_compose_* docker volumes (RAGFlow data)

    This is destructive to PROD data; caller must do double confirmation in UI.
    """
    log_lines: list[str] = []

    def log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] {msg}"
        log_lines.append(line)
        if log_cb is not None:
            try:
                log_cb(line)
            except Exception:
                # Never let UI logging crash the publish flow.
                pass

    def finish(ok: bool, before: ServerVersionInfo | None, after: ServerVersionInfo | None) -> PublishResult:
        return PublishResult(ok=ok, log="\n".join(log_lines), version_before=before, version_after=after)

    before = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    tag = (version or time.strftime("%Y%m%d_%H%M%S", time.localtime())).strip()

    log(f"DATA TEST={test_ip} -> PROD={prod_ip} VERSION={tag}")

    ok, test_base = _read_base_url(test_ip, app_dir=app_dir)
    if not ok:
        log(f"[PRECHECK] [ERROR] unable to read TEST base_url: {test_base}")
        return finish(False, before, None)
    log(f"[PRECHECK] TEST base_url: {test_base}")
    if (TEST_SERVER_IP not in test_base) and ("localhost" not in test_base) and ("127.0.0.1" not in test_base):
        log(f"[PRECHECK] [ERROR] TEST base_url mismatch; refusing to publish data.")
        return finish(False, before, None)

    desired_prod = f"http://{PROD_SERVER_IP}:{ragflow_port}"
    if not _ensure_prod_base_url(prod_ip, app_dir=app_dir, desired=desired_prod, log=log):
        log("[PRECHECK] [ERROR] unable to ensure PROD base_url; refusing to publish data.")
        return finish(False, before, None)

    ok = run_publish_data_pipeline(
        test_ip=test_ip,
        prod_ip=prod_ip,
        app_dir=app_dir,
        tag=tag,
        default_server_user=DEFAULT_SERVER_USER,
        log=log,
        ssh_fn=_ssh,
        run_local_fn=lambda argv: _run_local(argv, timeout_s=7200),
        stop_services_and_verify_fn=lambda ip, *, app_dir, log, who: _stop_services_and_verify(
            ip, app_dir=app_dir, log=log, who=who
        ),
        ensure_ragflow_running_on_prod_fn=lambda prod_ip, *, app_dir, log: _ensure_ragflow_running_on_prod(
            prod_ip, app_dir=app_dir, log=log
        ),
        ensure_ragflowauth_running_on_prod_fn=lambda prod_ip, *, log: _ensure_ragflowauth_running_on_prod(prod_ip, log=log),
        staging_manager_cls=RemoteStagingManager,
    )
    if not ok:
        return finish(False, before, None)

    after = get_server_version_info(server_ip=prod_ip, app_dir=app_dir)
    log("Publish data completed")
    return finish(True, before, after)
