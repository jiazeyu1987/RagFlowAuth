from __future__ import annotations

from typing import Callable

from tool.maintenance.features.onlyoffice_deploy_models import DeployOnlyOfficePipelineArtifacts


def transfer_and_load_image(
    *,
    server_ip: str,
    server_user: str,
    tar_size: int,
    artifacts: DeployOnlyOfficePipelineArtifacts,
    log,
    run_local_fn: Callable[[list[str], int], tuple[bool, str]],
    ssh_cmd_fn: Callable[[str, int], tuple[bool, str]],
    quote_part_fn: Callable[[str], str],
    staging_manager_cls,
) -> bool:
    log("[3/8] Pick remote staging path")
    staging_mgr = staging_manager_cls(exec_fn=lambda command: ssh_cmd_fn(command, 120), log=log)
    staging_mgr.cleanup_legacy_tmp_release_files()
    pick = staging_mgr.pick_dir_for_bytes(size_bytes=tar_size)
    artifacts.tar_remote = staging_mgr.join(pick.dir, artifacts.tar_local.name)
    log(f"[STAGING] remote tar path: {artifacts.tar_remote}")

    log("[4/8] Transfer image to target server (scp)")
    ok, out = run_local_fn(
        ["scp", str(artifacts.tar_local), f"{server_user}@{server_ip}:{artifacts.tar_remote}"],
        7200,
    )
    if not ok:
        log(f"[ERROR] scp failed:\n{out}")
        return False

    log("[5/8] Load image on target server (docker load)")
    ok, out = ssh_cmd_fn(f"docker load -i {quote_part_fn(artifacts.tar_remote)}", 7200)
    if not ok:
        log(f"[ERROR] docker load failed:\n{out}")
        return False
    staging_mgr.cleanup_path(artifacts.tar_remote)
    artifacts.tar_remote = ""
    return True
