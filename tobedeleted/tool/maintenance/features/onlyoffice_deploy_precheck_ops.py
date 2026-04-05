from __future__ import annotations

import time
from typing import Callable

from tool.maintenance.features.onlyoffice_deploy_models import DeployOnlyOfficePipelineArtifacts


def check_or_pull_local_image(
    *,
    image: str,
    log,
    run_local_fn: Callable[[list[str], int], tuple[bool, str]],
) -> bool:
    log("[1/8] Check local onlyoffice image")
    ok, out = run_local_fn(["docker", "image", "inspect", image], 60)
    if not ok:
        log("[INFO] local image missing, pulling from registry")
        ok, out = run_local_fn(["docker", "pull", image], 7200)
        if not ok:
            log(f"[ERROR] docker pull failed:\n{out}")
            return False
    return True


def export_local_image_tar(
    *,
    image: str,
    artifacts: DeployOnlyOfficePipelineArtifacts,
    log,
    run_local_fn: Callable[[list[str], int], tuple[bool, str]],
    make_temp_dir_fn,
) -> tuple[bool, int]:
    log("[2/8] Export local onlyoffice image (docker save)")
    artifacts.tmp_dir = make_temp_dir_fn(prefix="onlyoffice_release")
    tag = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    artifacts.tar_local = artifacts.tmp_dir / f"onlyoffice_release_{tag}.tar"
    ok, out = run_local_fn(["docker", "save", image, "-o", str(artifacts.tar_local)], 7200)
    if not ok or (not artifacts.tar_local.exists()):
        log(f"[ERROR] docker save failed:\n{out}")
        return False, 0
    tar_size = int(artifacts.tar_local.stat().st_size)
    log(f"[STAGING] local tar size: {tar_size} bytes")
    return True, tar_size
