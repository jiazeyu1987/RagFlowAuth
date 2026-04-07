import time

from .postcheck import run_restore_postcheck


def verify_restore_phase_7(self, *, ragflowauth_reason, log_to_file, messagebox):
    ragflowauth_ok = False

    # 7. 验证
    self.append_restore_log("\n[7/7] 验证服务状态...")
    self.update_restore_status("正在验证服务...")
    time.sleep(3)  # 等待容器完全启动

    # 容器状态
    success, output = self.ssh_executor.execute(
        "docker ps --no-trunc 2>&1 | grep -E '(ragflowauth-|ragflow_compose-)' 2>&1 || true"
    )
    if output:
        self.append_restore_log(output)

    # RagflowAuth 健康检查
    success, health = self.ssh_executor.execute("curl -fsS http://127.0.0.1:8001/health >/dev/null && echo OK || echo FAIL")
    health = (health or "").strip()
    if health == "OK":
        ragflowauth_ok = True
        self.append_restore_log("✅ RagflowAuth 后端健康检查: OK")
    else:
        if not ragflowauth_reason:
            ragflowauth_reason = "RagflowAuth 后端健康检查失败（/health 未通过）"
        self.append_restore_log(f"⚠️  RagflowAuth 后端健康检查: {health or 'FAIL'}")
        success, backend_logs = self.ssh_executor.execute("docker logs --tail 80 ragflowauth-backend 2>/dev/null || true")
        if backend_logs:
            self.append_restore_log("---- ragflowauth-backend logs (tail 80) ----")
            self.append_restore_log(backend_logs)

    _report_restore_completion(
        self,
        ragflowauth_ok=ragflowauth_ok,
        ragflowauth_reason=ragflowauth_reason,
        log_to_file=log_to_file,
        messagebox=messagebox,
    )


def _report_restore_completion(self, *, ragflowauth_ok, ragflowauth_reason, log_to_file, messagebox):
    # 完成
    self.append_restore_log("\n" + "=" * 60)
    if ragflowauth_ok:
        self.append_restore_log("✅ 数据还原完成！")
    else:
        self.append_restore_log("⚠️  数据已还原完成，但 RagflowAuth 未正常启动（请检查日志/先发布镜像后再启动）。")
    self.append_restore_log("=" * 60)
    self.update_restore_status("✅ 还原完成" if ragflowauth_ok else "⚠️ 还原完成（RagflowAuth 未启动）")

    # 显示消息（目标固定：测试服务器）
    success_msg = "数据还原已完成。\n\n可以访问以下地址验证：\n"
    success_msg += f"• RagflowAuth 前端: http://{self.restore_target_ip}:3001\n"
    success_msg += f"• RagflowAuth 后端: http://{self.restore_target_ip}:8001\n"
    if self.restore_volumes_exists:
        success_msg += f"• RAGFlow: http://{self.restore_target_ip}\n"
    success_msg += "\n提示：RAGFlow 服务可能需要 1-2 分钟完全启动"
    if not ragflowauth_ok:
        success_msg += f"\n\n⚠️ RagflowAuth 未正常启动：{ragflowauth_reason or '请查看日志'}"

    msg = f"[INFO] 数据还原完成\\n{success_msg}"
    print(msg)
    log_to_file(msg)
    # Post-check: enforce TEST base_url after restore (defensive).
    run_restore_postcheck(self)
    messagebox.showinfo("还原完成", success_msg)
