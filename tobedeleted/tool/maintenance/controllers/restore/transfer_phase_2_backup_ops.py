import time


def backup_existing_server_data(self):
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    backup_dir = f"/tmp/restore_backup_{timestamp}"

    commands = [
        f"mkdir -p {backup_dir}",
        "cp /opt/ragflowauth/data/auth.db /opt/ragflowauth/data/auth.db.backup 2>/dev/null || true",
        f"cp /opt/ragflowauth/data/auth.db {backup_dir}/ 2>/dev/null || true",
    ]

    for cmd in commands:
        success, output = self.ssh_executor.execute(cmd)
        self.append_restore_log(f"  {cmd}")
        if not success:
            self.append_restore_log(f"  ⚠️  警告: {output}")

    self.append_restore_log(f"✅ RagflowAuth 数据已备份到: {backup_dir}")
