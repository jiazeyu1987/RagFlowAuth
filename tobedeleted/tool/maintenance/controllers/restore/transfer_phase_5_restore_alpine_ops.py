def ensure_alpine_image_for_volume_restore(self):
    # 先检查是否有 alpine 镜像
    self.append_restore_log("    检查 alpine 镜像...")
    check_alpine_cmd = "docker images | grep alpine || echo 'NOT_FOUND'"
    success, alpine_output = self.ssh_executor.execute(check_alpine_cmd)
    if "NOT_FOUND" not in alpine_output:
        self.append_restore_log("    ✅ alpine 镜像已存在")
        return

    self.append_restore_log("    ⚠️  未找到 alpine 镜像，正在拉取（这可能需要几分钟）...")
    self.append_restore_log("    提示：首次运行会自动拉取 alpine 镜像，请耐心等待")
    pull_cmd = "docker pull alpine:latest"
    success, pull_output = self.ssh_executor.execute(pull_cmd)
    if not success:
        self.append_restore_log(f"    ❌ 拉取 alpine 镜像失败: {pull_output}")
        raise Exception(f"拉取 alpine 镜像失败: {pull_output}")
    self.append_restore_log("    ✅ alpine 镜像拉取完成")
