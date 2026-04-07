from __future__ import annotations

from typing import Any, Callable

from tool.maintenance.core.ssh_executor import build_scp_argv


def _dedupe_images(images: list[str]) -> list[str]:
    uniq: list[str] = []
    for image in images:
        if image and image not in uniq:
            uniq.append(image)
    return uniq


def run_image_transfer_pipeline(
    *,
    test_ip: str,
    prod_ip: str,
    app_dir: str,
    tag: str,
    backend_image: str,
    frontend_image: str,
    ragflow_images: list[str],
    default_server_user: str,
    default_staging_dir: str,
    log: Callable[[str], None],
    staging_manager_cls: Callable[..., Any],
    ssh_cmd: Callable[[str, str], tuple[bool, str]],
    run_local: Callable[[list[str]], tuple[bool, str]],
) -> tuple[bool, str]:
    releases_dir = f"{app_dir}/releases"

    staging_test = staging_manager_cls(exec_fn=lambda c, ip=test_ip: ssh_cmd(ip, c), log=log)
    staging_prod = staging_manager_cls(exec_fn=lambda c, ip=prod_ip: ssh_cmd(ip, c), log=log)

    log("[CLEANUP] pre-clean legacy /tmp release artifacts on TEST/PROD (best-effort)")
    staging_test.cleanup_legacy_tmp_release_files()
    staging_prod.cleanup_legacy_tmp_release_files()

    # Store large image tar on the biggest writable partition (avoid filling rootfs).
    # We don't know the final tar size upfront here, so pick the best dir by free space.
    pick_test = staging_test.pick_best_dir()
    pick_prod = staging_prod.pick_best_dir()
    tar_on_test = staging_test.join(pick_test.dir, f"ragflowauth_release_{tag}.tar")
    tar_on_prod = staging_prod.join(pick_prod.dir, f"ragflowauth_release_{tag}.tar")
    log(f"[STAGING] TEST tar path: {tar_on_test}")
    log(f"[STAGING] PROD tar path: {tar_on_prod}")

    log("[1/6] Ensure release directories")
    ok, out = ssh_cmd(test_ip, f"mkdir -p {releases_dir} && echo OK")
    if not ok:
        return False, f"TEST mkdir failed: {out}"
    ok, out = ssh_cmd(prod_ip, f"mkdir -p {releases_dir} && echo OK")
    if not ok:
        return False, f"PROD mkdir failed: {out}"

    # Ensure staging dirs exist (best-effort).
    ssh_cmd(test_ip, f"mkdir -p {default_staging_dir} 2>/dev/null || true")
    ssh_cmd(prod_ip, f"mkdir -p {default_staging_dir} 2>/dev/null || true")

    log("[2/6] Export images on TEST (docker save)")
    images_str = " ".join(_dedupe_images([backend_image, frontend_image] + ragflow_images))
    ok, out = ssh_cmd(
        test_ip,
        f"rm -f {tar_on_test} && docker save {images_str} -o {tar_on_test}",
    )
    if not ok:
        return False, f"docker save failed: {out}"

    log("[3/6] Transfer images TEST -> PROD (scp -3)")
    log(f"scp tar: {default_server_user}@{test_ip}:{tar_on_test} -> {default_server_user}@{prod_ip}:{tar_on_prod}")
    ok, out = run_local(
        build_scp_argv(
            f"{default_server_user}@{test_ip}:{tar_on_test}",
            f"{default_server_user}@{prod_ip}:{tar_on_prod}",
            through_local=True,
        )
    )
    if not ok:
        return False, f"scp tar failed: {out}"

    # Cleanup TEST tar after successful transfer (avoid filling rootfs).
    staging_test.cleanup_path(tar_on_test)

    log("[4/6] Load images on PROD (docker load)")
    ok, out = ssh_cmd(prod_ip, f"docker load -i {tar_on_prod}")
    if not ok:
        return False, f"docker load failed: {out}"

    # Cleanup PROD tar after successful load.
    staging_prod.cleanup_path(tar_on_prod)
    return True, "OK"
