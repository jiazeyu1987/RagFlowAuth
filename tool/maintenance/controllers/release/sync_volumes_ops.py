def restore_volumes_on_test(
    *,
    has_volumes,
    volumes_dir,
    ts,
    ssh_exec,
    subprocess_mod,
    tempfile_mod,
    tarfile_mod,
    path_cls,
    test_server_ip,
    ui_log,
):
    # 3) Restore ragflow volumes (if present)
    if not has_volumes:
        return

    ui_log("[SYNC] [3/5] Restore RAGFlow volumes on TEST")
    tmp_tar = path_cls(tempfile_mod.mkdtemp(prefix="ragflowauth_sync_")) / "volumes.tar.gz"
    with tarfile_mod.open(tmp_tar, "w:gz") as tar:
        tar.add(str(volumes_dir), arcname="volumes")

    ssh_exec("mkdir -p /var/lib/docker/tmp >/dev/null 2>&1 || true")
    scp_cmd2 = [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        str(tmp_tar),
        f"root@{test_server_ip}:/var/lib/docker/tmp/volumes.tar.gz",
    ]
    proc2 = subprocess_mod.run(scp_cmd2, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc2.returncode != 0:
        raise RuntimeError(f"SCP volumes.tar.gz 失败: {(proc2.stderr or proc2.stdout or '').strip()}")

    # Avoid /tmp (often on rootfs). Use docker tmp dir when possible.
    workdir = f"/var/lib/docker/tmp/ragflowauth_restore_{ts}"
    okx, outx = ssh_exec(
        f"rm -rf {workdir}; mkdir -p {workdir} && "
        f"tar -xzf /var/lib/docker/tmp/volumes.tar.gz -C {workdir} && "
        f"rm -f /var/lib/docker/tmp/volumes.tar.gz && echo OK"
    )
    if not okx:
        raise RuntimeError(f"解压 volumes.tar.gz 失败: {outx}")

    restore_cmd = r"""
set -e
docker image inspect alpine >/dev/null 2>&1 || docker pull alpine:latest >/dev/null 2>&1 || true
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
""".strip().format(workdir=workdir)
    okr, outr = ssh_exec(restore_cmd)
    if not okr:
        raise RuntimeError(f"还原 volumes 失败:\n{outr}")
    if (outr or "").strip():
        ui_log((outr or "").strip())
    ssh_exec(f"rm -rf {workdir} 2>/dev/null || true")
