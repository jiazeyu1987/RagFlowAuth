import sys

from .transfer_phase_5_upload_posix_ops import upload_volumes_archive_linux_mac
from .transfer_phase_5_upload_windows_ops import upload_volumes_archive_windows


def create_volumes_archive(self, *, volumes_local, tempfile_mod, tarfile_mod, os_mod):
    # 在本地打包 volumes 目录
    self.append_restore_log("  [步骤 4/6] 打包本地 volumes 目录...")
    self.append_restore_log("    创建临时文件...")
    temp_tar = tempfile_mod.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    temp_tar_path = temp_tar.name
    temp_tar.close()
    self.append_restore_log(f"    临时文件: {temp_tar_path}")

    self.append_restore_log(f"    开始压缩: {volumes_local} -> {temp_tar_path}")
    with tarfile_mod.open(temp_tar_path, "w:gz") as tar:
        tar.add(volumes_local, arcname="volumes")

    size_mb = os_mod.path.getsize(temp_tar_path) / 1024 / 1024
    self.append_restore_log(f"    ✅ 压缩完成，大小: {size_mb:.2f} MB")
    return temp_tar_path, size_mb


def upload_volumes_archive(self, *, temp_tar_path, size_mb, subprocess_mod, time_mod, log_to_file):
    # 上传压缩包到服务器
    self.append_restore_log("  [步骤 5/6] 上传压缩包到服务器...")
    self.append_restore_log(f"    目标: {self.restore_target_user}@{self.restore_target_ip}:/var/lib/docker/tmp/volumes.tar.gz")
    self.append_restore_log(f"    预计需要时间: {size_mb:.2f} MB / 网络速度 ≈ 10秒 ~ 1分钟")

    start_time = time_mod.time()

    # 方案: 使用 pscp (PuTTY) 或 scp with SSH key
    # 先检查是否在 Windows 上
    is_windows = sys.platform == "win32"
    self.append_restore_log(f"    平台检测: {'Windows' if is_windows else 'Linux/Mac'}")

    try:
        if is_windows:
            upload_volumes_archive_windows(
                self,
                temp_tar_path=temp_tar_path,
                size_mb=size_mb,
                subprocess_mod=subprocess_mod,
                time_mod=time_mod,
                start_time=start_time,
                log_to_file=log_to_file,
            )
        else:
            upload_volumes_archive_linux_mac(
                self,
                temp_tar_path=temp_tar_path,
                subprocess_mod=subprocess_mod,
                time_mod=time_mod,
                start_time=start_time,
            )
    except Exception as e:
        elapsed = time_mod.time() - start_time
        raise Exception(f"上传失败 (耗时: {elapsed:.1f}秒): {str(e)}")


def cleanup_temp_archive(temp_tar_path, *, os_mod):
    # 删除本地临时文件
    if os_mod.path.exists(temp_tar_path):
        os_mod.remove(temp_tar_path)
