def upload_volumes_archive_windows(self, *, temp_tar_path, size_mb, subprocess_mod, time_mod, start_time, log_to_file):
    # Windows: 使用 PowerShell + WinSCP-Portable 或直接 scp
    self.append_restore_log("    检测到 Windows，使用 SCP...")

    # 检查 scp 是否可用
    self.append_restore_log("    检查 scp 命令...")
    scp_check = subprocess_mod.run(["where", "scp"], capture_output=True, text=True, shell=True)
    self.append_restore_log(f"    where scp 返回码: {scp_check.returncode}")

    if scp_check.returncode != 0:
        error_msg = (
            "Windows 上找不到 scp 命令。\n\n"
            "解决方案：\n"
            "1. 安装 Git for Windows（包括 Git Bash）\n"
            "2. 或安装 WSL (Windows Subsystem for Linux)\n"
            "3. 或使用 WinSCP 图形界面手动上传文件"
        )
        self.append_restore_log(f"    ❌ {error_msg}")
        raise Exception(error_msg)

    scp_path = scp_check.stdout.strip()
    self.append_restore_log(f"    ✅ 找到 scp: {scp_path}")

    # 方案1: 尝试使用 scp（如果有 Git Bash 或 WSL）
    self.append_restore_log("    准备执行 SCP 命令...")
    self.append_restore_log(f"    源文件: {temp_tar_path}")
    self.append_restore_log(f"    目标: {self.restore_target_user}@{self.restore_target_ip}:/var/lib/docker/tmp/volumes.tar.gz")

    cmd = [
        "scp",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "BatchMode=yes",
        temp_tar_path,
        f"{self.restore_target_user}@{self.restore_target_ip}:/var/lib/docker/tmp/volumes.tar.gz",
    ]
    self.append_restore_log(f"    命令: {' '.join(cmd)}")

    result = subprocess_mod.run(
        cmd,
        capture_output=True,
        text=True,
    )

    elapsed = time_mod.time() - start_time
    self.append_restore_log(f"    SCP 执行完成，耗时: {elapsed:.1f}秒")
    self.append_restore_log(f"    SCP 退出码: {result.returncode}")

    if result.returncode == 0:
        self.append_restore_log(f"    ✅ 上传成功 (耗时: {elapsed:.1f}秒)")
        log_to_file(f"[RESTORE] volumes.tar.gz 上传完成: {size_mb:.2f} MB 用时 {elapsed:.1f} 秒 ({size_mb/elapsed:.2f} MB/s)")
        return

    # SCP 失败，显示详细错误
    stdout = result.stdout.strip() if result.stdout else "(空)"
    stderr = result.stderr.strip() if result.stderr else "(空)"
    self.append_restore_log("    ❌ SCP 失败")
    self.append_restore_log(f"    stdout: {stdout}")
    self.append_restore_log(f"    stderr: {stderr}")

    if "Permission denied" in stderr or "password" in stderr.lower():
        error_msg = (
            "SCP 需要 SSH 密钥认证。\n"
            f"错误: {stderr}\n\n"
            "解决方案：\n"
            "1. 生成 SSH 密钥: ssh-keygen -t rsa -b 4096\n"
            f"2. 复制公钥到服务器: ssh-copy-id {self.restore_target_user}@{self.restore_target_ip}\n"
            f"3. 或手动复制: type C:\\Users\\<用户>\\.ssh\\id_rsa.pub | ssh {self.restore_target_user}@{self.restore_target_ip} 'cat >> ~/.ssh/authorized_keys'"
        )
        self.append_restore_log(f"    ❌ {error_msg}")
        raise Exception(error_msg)

    error_msg = f"上传失败 (退出码: {result.returncode}):\nstdout: {stdout}\nstderr: {stderr}"
    self.append_restore_log(f"    ❌ {error_msg}")
    raise Exception(error_msg)
