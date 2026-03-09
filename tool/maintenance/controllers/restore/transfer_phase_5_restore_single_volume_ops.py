def restore_single_volume_archive(self, *, tar_filename, idx, total):
    volume_name = tar_filename.replace(".tar.gz", "")
    self.append_restore_log(f"\n    [{idx}/{total}] 还原 volume: {volume_name}")
    self.append_restore_log(f"      文件: {tar_filename}")

    # 检查文件大小（使用 stat 避免 awk 转义问题）
    size_cmd = f"stat -c %s /opt/ragflowauth/ragflow_compose/volumes/{tar_filename} 2>/dev/null || echo '0'"
    success, size_output = self.ssh_executor.execute(size_cmd)
    if success and size_output.strip().isdigit():
        size_bytes = int(size_output.strip())
        size_mb = size_bytes / 1024 / 1024
        self.append_restore_log(f"      大小: {size_mb:.2f} MB")
    else:
        self.append_restore_log("      大小: (无法获取)")

    self.append_restore_log("      开始解压（预计 1-3 分钟）...")

    # 还原单个 volume（使用更长的超时：15分钟）
    # 完全避免引号问题：直接使用 tar 命令，不用 sh -c
    restore_single_cmd = (
        f"docker run --rm "
        f"-v {volume_name}:/data "
        f"-v /opt/ragflowauth/ragflow_compose/volumes:/backup:ro "
        f"alpine tar -xzf /backup/{tar_filename} -C /data 2>&1"
    )
    self.append_restore_log("      执行还原命令（超时 15 分钟）...")
    # Volume 还原可能需要很长时间，设置 15 分钟超时
    success, output = self.ssh_executor.execute(restore_single_cmd, timeout_seconds=900)
    if success:
        self.append_restore_log(f"      ✅ {volume_name} 还原成功")
        return True

    self.append_restore_log(f"      ⚠️  {volume_name} 还原失败:")
    self.append_restore_log(f"      错误输出:\n{output}")
    return False
