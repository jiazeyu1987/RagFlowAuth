def extract_remote_volumes_archive(self):
    self.append_restore_log("    在服务器上解压 volumes.tar.gz...")
    extract_cmd = (
        "cd /opt/ragflowauth/ragflow_compose && "
        "tar -xzf /var/lib/docker/tmp/volumes.tar.gz && "
        "rm -f /var/lib/docker/tmp/volumes.tar.gz"
    )
    self.append_restore_log(f"    执行: {extract_cmd}")
    success, output = self.ssh_executor.execute(extract_cmd)
    if not success:
        self.append_restore_log(f"    ❌ 解压失败: {output}")
        raise Exception(f"解压 volumes.tar.gz 失败: {output}")

    self.append_restore_log("    ✅ 解压成功")
    if output:
        self.append_restore_log(f"    输出: {output}")


def stop_ragflow_containers_for_restore(self):
    # 停止 RAGFlow 容器（防止还原时的写入冲突）
    self.append_restore_log("    停止 RAGFlow 容器（防止还原冲突）...")
    stop_cmd = "cd /opt/ragflowauth/ragflow_compose && docker compose down"
    self.append_restore_log(f"    执行: {stop_cmd}")
    success, output = self.ssh_executor.execute(stop_cmd)
    if success:
        self.append_restore_log("    ✅ RAGFlow 容器已停止")
        return

    self.append_restore_log("    ⚠️  停止 RAGFlow 容器时出现警告（可能已停止）")
    if output:
        self.append_restore_log(f"    输出: {output}")
