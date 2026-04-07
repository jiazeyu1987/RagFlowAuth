def prepare_restore_volumes_workspace(self):
    # 先确保服务器上的目录存在
    self.append_restore_log("  [步骤 1/6] 准备服务器目录...")
    self.append_restore_log("    执行: mkdir -p /opt/ragflowauth/ragflow_compose")
    success, output = self.ssh_executor.execute("mkdir -p /opt/ragflowauth/ragflow_compose")
    if success:
        self.append_restore_log("    ✅ 目录创建成功")
    else:
        self.append_restore_log(f"    ⚠️  目录创建输出: {output}")

    # 先备份服务器上的 RAGFlow volumes（如果存在）
    self.append_restore_log("  [步骤 2/6] 备份服务器上的 RAGFlow volumes...")
    backup_cmd = (
        "cd /opt/ragflowauth/ragflow_compose && "
        "tar -czf /var/lib/docker/tmp/ragflow_volumes_backup_$(date +%Y%m%d_%H%M%S).tar.gz volumes 2>/dev/null || true"
    )
    self.append_restore_log(f"    执行: {backup_cmd}")
    success, output = self.ssh_executor.execute(backup_cmd)
    if success:
        self.append_restore_log("    ✅ 备份成功")
    else:
        self.append_restore_log(f"    ⚠️  备份输出: {output}")

    # 删除服务器上的旧 volumes 目录（如果存在）
    self.append_restore_log("  [步骤 3/6] 清理服务器上的旧 volumes目录...")
    self.append_restore_log("    执行: rm -rf /opt/ragflowauth/ragflow_compose/volumes")
    success, output = self.ssh_executor.execute("rm -rf /opt/ragflowauth/ragflow_compose/volumes")
    if success:
        self.append_restore_log("    ✅ 清理成功")
    else:
        self.append_restore_log(f"    ⚠️  清理输出: {output}")
