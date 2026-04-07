def upload_volumes_archive_linux_mac(self, *, temp_tar_path, subprocess_mod, time_mod, start_time):
    # Linux/Mac: 直接使用 scp
    self.append_restore_log("    使用 SCP 上传 (Linux/Mac)...")
    result = subprocess_mod.run(
        [
            "scp",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            temp_tar_path,
            f"{self.restore_target_user}@{self.restore_target_ip}:/var/lib/docker/tmp/volumes.tar.gz",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout
        self.append_restore_log(f"    ❌ 上传失败: {error_msg}")
        raise Exception(f"上传失败: {error_msg}")

    elapsed = time_mod.time() - start_time
    self.append_restore_log(f"    ✅ 上传完成 (耗时: {elapsed:.1f}秒)")
