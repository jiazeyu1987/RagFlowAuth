from __future__ import annotations

import time
from typing import Callable

from tool.maintenance.core.ssh_executor import build_scp_argv


def run_publish_data_pipeline(
    *,
    test_ip: str,
    prod_ip: str,
    app_dir: str,
    tag: str,
    default_server_user: str,
    log,
    ssh_fn: Callable[[str, str], tuple[bool, str]],
    run_local_fn: Callable[[list[str]], tuple[bool, str]],
    stop_services_and_verify_fn,
    ensure_ragflow_running_on_prod_fn,
    ensure_ragflowauth_running_on_prod_fn,
    staging_manager_cls,
) -> bool:
    staging_test = staging_manager_cls(exec_fn=lambda c: ssh_fn(test_ip, c), log=log)
    staging_prod = staging_manager_cls(exec_fn=lambda c: ssh_fn(prod_ip, c), log=log)

    workdir_test: str | None = None
    tar_test: str | None = None
    workdir_prod: str | None = None
    tar_prod: str | None = None

    def cleanup_best_effort() -> None:
        # Only cleanup our temporary artifacts (NEVER touch backups or /opt/ragflowauth/data/backups).
        staging_test.cleanup_legacy_tmp_release_files()
        staging_prod.cleanup_legacy_tmp_release_files()
        ssh_fn(test_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        ssh_fn(prod_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        if tar_test:
            staging_test.cleanup_path(tar_test)
        if workdir_test:
            ssh_fn(test_ip, f"rm -rf {workdir_test} 2>/dev/null || true")
        if tar_prod:
            staging_prod.cleanup_path(tar_prod)
        if workdir_prod:
            ssh_fn(prod_ip, f"rm -rf {workdir_prod} 2>/dev/null || true")

    try:
        log("[PRECHECK] Clean legacy tmp artifacts (best-effort)")
        staging_test.cleanup_legacy_tmp_release_files()
        staging_prod.cleanup_legacy_tmp_release_files()
        ssh_fn(test_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")
        ssh_fn(prod_ip, "rm -rf /tmp/ragflowauth_data_release_* 2>/dev/null || true")

        # Pick staging dirs on both servers to avoid filling rootfs (/tmp is often on /).
        pick_test = staging_test.pick_best_dir()
        pick_prod = staging_prod.pick_best_dir()

        workdir_test = staging_test.join(pick_test.dir, f"ragflowauth_data_release_{tag}")
        tar_test = staging_test.join(pick_test.dir, f"ragflowauth_data_release_{tag}.tar.gz")
        workdir_prod = staging_prod.join(pick_prod.dir, f"ragflowauth_data_release_{tag}")
        tar_prod = staging_prod.join(pick_prod.dir, f"ragflowauth_data_release_{tag}.tar.gz")

        log("[1/7] Prepare pack dir on TEST")
        ok, out = ssh_fn(test_ip, f"rm -rf {workdir_test} {tar_test}; mkdir -p {workdir_test}/volumes && echo OK")
        if not ok:
            log(f"[ERROR] TEST prepare failed: {out}")
            return False

        log("[2/7] Stop services on TEST (for consistent snapshot)")
        if not stop_services_and_verify_fn(test_ip, app_dir=app_dir, log=log, who="TEST"):
            log("[ERROR] TEST services did not stop cleanly; aborting to avoid inconsistent snapshot")
            return False

        log("[3/7] Export auth.db + ragflow volumes on TEST")
        ok, out = ssh_fn(
            test_ip,
            f"cp -f {app_dir}/data/auth.db {workdir_test}/auth.db 2>/dev/null || true; ls -lh {workdir_test}/auth.db 2>&1 || true",
        )
        if not ok:
            log(f"[ERROR] copy auth.db on TEST failed: {out}")
            return False

        export_cmd = r"""
set -e
mkdir -p "{workdir}/volumes"
docker image inspect alpine >/dev/null 2>&1 || docker pull alpine:latest >/dev/null 2>&1 || true
vols=$(docker volume ls --format '{{{{.Name}}}}' | grep '^ragflow_compose_' || true)
if [ -z "$vols" ]; then
  echo "NO_VOLUMES"
  exit 0
fi
for v in $vols; do
  echo "EXPORT $v"
  docker run --rm -v "$v:/data:ro" -v "{workdir}/volumes:/backup" alpine sh -lc "cd /data && tar -czf /backup/${{v}}.tar.gz ."
done
""".strip().format(workdir=workdir_test)
        ok, out = ssh_fn(test_ip, export_cmd)
        if not ok:
            log(f"[ERROR] export volumes on TEST failed:\n{out}")
            return False
        if out.strip():
            log(out.strip())

        log("[4/7] Pack data tar on TEST")
        ok, out = ssh_fn(test_ip, f"tar -czf {tar_test} -C {workdir_test} auth.db volumes && ls -lh {tar_test} 2>&1 || true")
        if not ok:
            log(f"[ERROR] tar pack on TEST failed: {out}")
            return False

        # Free TEST workdir ASAP (tar already created).
        ssh_fn(test_ip, f"rm -rf {workdir_test} 2>/dev/null || true")
        workdir_test = None

        log("[5/7] Transfer data tar TEST -> PROD (scp -3)")
        scp_cmd = build_scp_argv(
            f"{default_server_user}@{test_ip}:{tar_test}",
            f"{default_server_user}@{prod_ip}:{tar_prod}",
            through_local=True,
        )
        ok, out = run_local_fn(scp_cmd)
        if not ok:
            log(f"[ERROR] scp -3 failed: {out}")
            return False

        # Remove TEST tar after transfer succeeds.
        staging_test.cleanup_path(tar_test)
        tar_test = None

        log("[6/7] Apply on PROD (stop, backup, restore)")

        # Stop services (strict)
        if not stop_services_and_verify_fn(prod_ip, app_dir=app_dir, log=log, who="PROD"):
            log("[ERROR] PROD services did not stop cleanly; aborting to avoid partial restore")
            return False

        # Backup current db (best-effort)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        ssh_fn(
            prod_ip,
            f"mkdir -p /tmp/restore_backup_{ts} >/dev/null 2>&1 || true; "
            f"cp -f {app_dir}/data/auth.db /tmp/restore_backup_{ts}/auth.db 2>/dev/null || true",
        )

        ok, out = ssh_fn(
            prod_ip,
            f"rm -rf {workdir_prod}; mkdir -p {workdir_prod} && tar -xzf {tar_prod} -C {workdir_prod} && echo OK",
        )
        if not ok:
            log(f"[ERROR] extract on PROD failed: {out}")
            return False

        # Remove PROD tar after extraction succeeds.
        staging_prod.cleanup_path(tar_prod)
        tar_prod = None

        # Restore auth.db
        ok, out = ssh_fn(prod_ip, f"cp -f {workdir_prod}/auth.db {app_dir}/data/auth.db && echo OK")
        if not ok:
            log(f"[ERROR] restore auth.db on PROD failed: {out}")
            return False

        # Restore volumes
        restore_vol_cmd = r"""
set -e
if [ ! -d "{workdir}/volumes" ]; then
  echo "NO_VOLUMES_DIR"
  exit 0
fi
files=$(ls -1 "{workdir}/volumes"/*.tar.gz 2>/dev/null || true)
if [ -z "$files" ]; then
  echo "NO_VOLUME_TARS"
  exit 0
fi
for f in $files; do
  name=$(basename "$f" .tar.gz)
  echo "RESTORE $name"
  docker volume inspect "$name" >/dev/null 2>&1 || docker volume create "$name" >/dev/null
  docker run --rm -v "$name:/data" -v "{workdir}/volumes:/backup:ro" alpine sh -lc "rm -rf /data/* /data/.[!.]* /data/..?* 2>/dev/null || true; tar -xzf /backup/${{name}}.tar.gz -C /data"
done
""".strip().format(workdir=workdir_prod)
        ok, out = ssh_fn(prod_ip, restore_vol_cmd)
        if not ok:
            log(f"[ERROR] restore volumes on PROD failed:\n{out}")
            return False
        if out.strip():
            log(out.strip())

        log("[7/8] Restart services on PROD")
        if not ensure_ragflow_running_on_prod_fn(prod_ip, app_dir=app_dir, log=log):
            log("[ERROR] PROD ragflow services did not start cleanly; aborting")
            return False

        if not ensure_ragflowauth_running_on_prod_fn(prod_ip, log=log):
            log("[ERROR] PROD ragflowauth services did not start cleanly; aborting")
            return False

        log("[8/8] Cleanup temporary artifacts on PROD")
        ssh_fn(prod_ip, f"rm -rf {workdir_prod} 2>/dev/null || true")
        workdir_prod = None
        return True
    finally:
        cleanup_best_effort()
