import time


def start_ragflow_containers(self):
    # 启动 RAGFlow 容器（如果还原了 volumes）
    if self.restore_volumes_exists:
        self.append_restore_log("  启动 RAGFlow 容器...")
        success, output = self.ssh_executor.execute("cd /opt/ragflowauth/ragflow_compose && docker compose up -d")
        self.append_restore_log(f"  {output}")

        if success:
            self.append_restore_log("  ✅ RAGFlow 容器启动成功")
        else:
            self.append_restore_log("  ⚠️  RAGFlow 容器启动可能有问题，请检查日志")

        # 等待 RAGFlow 容器启动
        self.append_restore_log("  等待 RAGFlow 服务完全启动...")
        time.sleep(10)  # RAGFlow 需要更长时间启动
    else:
        self.append_restore_log("  跳过 RAGFlow 容器（未还原数据）")
