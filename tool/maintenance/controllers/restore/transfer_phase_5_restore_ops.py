from .transfer_phase_5_restore_extract_ops import (
    extract_remote_volumes_archive,
    stop_ragflow_containers_for_restore,
)
from .transfer_phase_5_restore_volumes_ops import restore_docker_volumes_from_archive


def extract_and_restore_remote_volumes(self):
    # 在服务器上解压
    self.append_restore_log("  [步骤 6/6] 解压并还原 volumes...")
    extract_remote_volumes_archive(self)
    stop_ragflow_containers_for_restore(self)
    restore_docker_volumes_from_archive(self)
    self.append_restore_log("  ✅ RAGFlow volumes 还原完成")
