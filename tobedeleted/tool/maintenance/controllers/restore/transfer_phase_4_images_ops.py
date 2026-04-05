def run_restore_phase_4_images(self, *, log_to_file, messagebox, tempfile, tarfile, subprocess, time, os):
    if self.restore_images_exists:
        self.append_restore_log("\n[4/7] 上传并加载 Docker 镜像...")
        self.update_restore_status("正在上传 Docker 镜像...")

        # 确保 Docker 磁盘挂载点存在
        self.ssh_executor.execute("mkdir -p /var/lib/docker/tmp")

        images_tar_local = self.selected_restore_folder / "images.tar"
        size_mb = images_tar_local.stat().st_size / 1024 / 1024
        self.append_restore_log(f"  上传 images.tar ({size_mb:.2f} MB) 到 /var/lib/docker/tmp...")

        # 上传到 Docker 磁盘挂载点
        import time
        start_time = time.time()

        result = subprocess.run(
            [
                "scp",
                "-o",
                "BatchMode=yes",
                str(images_tar_local),
                f"{self.restore_target_user}@{self.restore_target_ip}:/var/lib/docker/tmp/images.tar",
            ],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log_to_file(f"[RESTORE] 上传 images.tar 失败: {result.stderr}", "ERROR")
            raise Exception(f"上传 images.tar 失败: {result.stderr}")

        elapsed = time.time() - start_time
        self.append_restore_log("  ✅ images.tar 上传成功")
        log_to_file(f"[RESTORE] images.tar 上传完成: {size_mb:.2f} MB 用时 {elapsed:.1f} 秒 ({size_mb/elapsed:.2f} MB/s)")
        self.append_restore_log("  正在加载 Docker 镜像...")

        # 加载镜像
        success, output = self.ssh_executor.execute("docker load -i /var/lib/docker/tmp/images.tar")
        if success:
            self.append_restore_log("  ✅ Docker 镜像加载成功")
        else:
            raise Exception(f"加载 Docker 镜像失败: {output}")

        # 清理临时文件
        self.ssh_executor.execute("rm -f /var/lib/docker/tmp/images.tar")
    else:
        self.append_restore_log("\n[4/7] 跳过 Docker 镜像（未找到 images.tar）")

    # 4.5. 上传 RAGFlow volumes（如果存在）
