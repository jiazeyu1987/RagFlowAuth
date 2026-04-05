from .transfer_phase_1_stop_ops import stop_and_verify_services
from .transfer_phase_2_backup_ops import backup_existing_server_data
from .transfer_phase_3_upload_ops import upload_restore_auth_db


def run_restore_phases_1_to_3(self, *, log_to_file, messagebox, tempfile, tarfile, subprocess, time, os):
    self.append_restore_log("=" * 60)
    self.append_restore_log(f"开始还原: {self.selected_restore_folder}")
    self.append_restore_log("=" * 60)

    # 1. 停止容器
    self.append_restore_log("\n[1/7] 停止 Docker 容器...")
    self.update_restore_status("正在停止容器...")
    stop_and_verify_services(self, timeout_s=90)

    # 2. 备份服务器现有数据
    self.append_restore_log("\n[2/7] 备份服务器现有数据...")
    self.update_restore_status("正在备份现有数据...")
    backup_existing_server_data(self)

    # 3. 上传数据文件
    self.append_restore_log("\n[3/7] 上传 RagflowAuth 数据文件...")
    self.update_restore_status("正在上传 RagflowAuth 数据...")
    upload_restore_auth_db(self, subprocess_mod=subprocess)
