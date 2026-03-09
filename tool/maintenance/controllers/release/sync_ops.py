from pathlib import Path

from ._shared import _tool_mod
from .sync_precheck_ops import (
    build_ssh_exec,
    ensure_backup_payload,
    ensure_test_base_url,
    resolve_pack_dir,
)
from .sync_transfer_ops import (
    healthcheck_backend_on_test,
    restart_services_on_test,
    restore_volumes_on_test,
    stop_services_on_test,
    upload_auth_db_to_test,
)


def sync_local_backup_to_test(app, *, pack_dir: Path | None, ui_log) -> None:

    tool_mod = _tool_mod()
    self = app

    """
    Apply a local backup under D:\\datas\\RagflowAuth to the TEST server (data only):
    - auth.db
    - RAGFlow volumes (ragflow_compose_* docker volumes)

    IMPORTANT:
    - This must NOT restore images.tar (to avoid overriding freshly published images).
    - This is destructive to TEST data; caller must confirm in UI.
    """
    pack_dir = resolve_pack_dir(
        pack_dir=pack_dir,
        path_cls=tool_mod.Path,
        feature_list_local_backups=tool_mod.feature_list_local_backups,
        ui_log=ui_log,
    )
    auth_db, volumes_dir, has_volumes = ensure_backup_payload(pack_dir=pack_dir, ui_log=ui_log)

    # Use SSH to operate on TEST server.
    ssh, ssh_exec = build_ssh_exec(ssh_executor_cls=tool_mod.SSHExecutor, test_server_ip=tool_mod.TEST_SERVER_IP)
    ensure_test_base_url(ssh_exec=ssh_exec, test_server_ip=tool_mod.TEST_SERVER_IP, ui_log=ui_log)

    stop_services_on_test(
        service_controller_cls=tool_mod.ServiceController,
        ssh=ssh,
        ui_log=ui_log,
    )

    ts = upload_auth_db_to_test(
        auth_db=auth_db,
        ssh_exec=ssh_exec,
        subprocess_mod=tool_mod.subprocess,
        test_server_ip=tool_mod.TEST_SERVER_IP,
        time_mod=tool_mod.time,
        ui_log=ui_log,
    )

    restore_volumes_on_test(
        has_volumes=has_volumes,
        volumes_dir=volumes_dir,
        ts=ts,
        ssh_exec=ssh_exec,
        subprocess_mod=tool_mod.subprocess,
        tempfile_mod=tool_mod.tempfile,
        tarfile_mod=tool_mod.tarfile,
        path_cls=tool_mod.Path,
        test_server_ip=tool_mod.TEST_SERVER_IP,
        ui_log=ui_log,
    )

    restart_services_on_test(ssh_exec=ssh_exec, ui_log=ui_log)
    healthcheck_backend_on_test(ssh_exec=ssh_exec, ui_log=ui_log)

    # Post-check (defensive): enforce TEST base_url after sync.
    self._guard_ragflow_base_url(role="test", stage="LOCAL->TEST SYNC POST", ui_log=ui_log)
    try:
        self.root.after(0, self.refresh_ragflow_base_urls)
    except Exception:
        pass
