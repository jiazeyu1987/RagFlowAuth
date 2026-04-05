from .transfer_phase_5_restore_alpine_ops import ensure_alpine_image_for_volume_restore
from .transfer_phase_5_restore_single_volume_ops import restore_single_volume_archive


def restore_docker_volumes_from_archive(self):
    # 还原 Docker volumes（将 tar.gz 提取到实际的 Docker volume 中）
    self.append_restore_log("    还原 Docker volumes（提取到实际 volume）...")
    ensure_alpine_image_for_volume_restore(self)

    volume_files = _scan_restore_volume_files(self)
    if not volume_files:
        return

    # 逐个还原 volume（每个 volume 独立超时）
    restored_count = 0
    failed_volumes = []
    for i, tar_filename in enumerate(volume_files, 1):
        if restore_single_volume_archive(self, tar_filename=tar_filename, idx=i, total=len(volume_files)):
            restored_count += 1
        else:
            failed_volumes.append(tar_filename.replace(".tar.gz", ""))

    # 汇总结果
    self.append_restore_log("\n    Volume 还原完成:")
    self.append_restore_log(f"      成功: {restored_count}/{len(volume_files)}")
    if failed_volumes:
        self.append_restore_log(f"      失败: {', '.join(failed_volumes)}")
        if restored_count > 0:
            self.append_restore_log("      ⚠️  部分 volume 还原失败，但 RAGFlow 可能仍能正常工作")
        else:
            raise Exception(f"所有 volume 还原失败: {', '.join(failed_volumes)}")


def _scan_restore_volume_files(self):
    # 先列出要还原的 volumes
    self.append_restore_log("    扫描要还原的 volume 文件...")
    list_cmd = "ls -1 /opt/ragflowauth/ragflow_compose/volumes/*.tar.gz 2>/dev/null | xargs -n1 basename || echo 'NO_FILES'"
    success, list_output = self.ssh_executor.execute(list_cmd)
    if "NO_FILES" in list_output or not list_output.strip():
        self.append_restore_log("    ⚠️  未找到 volume 备份文件，跳过 volume 还原")
        return []

    # 过滤：只保留以 .tar.gz 结尾的行（排除 SSH 错误输出）
    volume_files = [line.strip() for line in list_output.strip().split("\n") if line.strip() and line.strip().endswith(".tar.gz")]
    self.append_restore_log(f"    找到 {len(volume_files)} 个 volume 文件:")
    for vf in volume_files:
        self.append_restore_log(f"      - {vf}")
    return volume_files
