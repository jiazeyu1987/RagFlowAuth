from .transfer_phase_5_prepare_ops import prepare_restore_volumes_workspace
from .transfer_phase_5_restore_ops import extract_and_restore_remote_volumes
from .transfer_phase_5_upload_ops import (
    cleanup_temp_archive,
    create_volumes_archive,
    upload_volumes_archive,
)


def run_restore_phase_5_volumes(self, *, log_to_file, messagebox, tempfile, tarfile, subprocess, time, os):
    if not self.restore_volumes_exists:
        self.append_restore_log("\n[5/7] 跳过 RAGFlow 数据（未找到 volumes）")
        return

    self.append_restore_log("\n[5/7] 上传 RAGFlow 数据 (volumes)...")
    self.update_restore_status("正在上传 RAGFlow 数据...")

    volumes_local = self.selected_restore_folder / "volumes"
    self.append_restore_log(f"  本地 volumes 目录: {volumes_local}")

    prepare_restore_volumes_workspace(self)
    temp_tar_path, size_mb = create_volumes_archive(
        self,
        volumes_local=volumes_local,
        tempfile_mod=tempfile,
        tarfile_mod=tarfile,
        os_mod=os,
    )
    try:
        upload_volumes_archive(
            self,
            temp_tar_path=temp_tar_path,
            size_mb=size_mb,
            subprocess_mod=subprocess,
            time_mod=time,
            log_to_file=log_to_file,
        )
        extract_and_restore_remote_volumes(self)
    finally:
        cleanup_temp_archive(temp_tar_path, os_mod=os)
