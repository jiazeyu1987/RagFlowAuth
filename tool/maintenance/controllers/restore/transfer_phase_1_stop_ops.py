import time


def stop_and_verify_services(self, *, timeout_s: int = 60) -> None:
    """
    Stop RagflowAuth + (optional) RAGFlow containers and verify they are NOT running.

    Why strict: restoring volumes while services are running can produce inconsistent snapshots,
    especially for Elasticsearch (ragflow_compose_esdata01), which later forces a re-chunk/reindex.
    """
    # Stop RagflowAuth containers (best-effort)
    self.append_restore_log("  [STOP] 停止 RagflowAuth 容器...")
    _, out1 = self.ssh_executor.execute("docker stop ragflowauth-backend ragflowauth-frontend 2>&1 || true")
    if (out1 or "").strip():
        self.append_restore_log(f"  {out1.strip()}")

    # Stop RAGFlow compose stack (best-effort)
    if self.restore_volumes_exists:
        self.append_restore_log("  [STOP] 停止 RAGFlow（docker compose down）...")
        _, out2 = self.ssh_executor.execute("cd /opt/ragflowauth/ragflow_compose 2>/dev/null && docker compose down 2>&1 || true")
        if (out2 or "").strip():
            self.append_restore_log(f"  {out2.strip()}")

    # Fallback: stop containers by name prefix (ragflow_compose-)
    if self.restore_volumes_exists:
        self.append_restore_log("  [STOP] 兜底停止 ragflow_compose-* 容器...")
        stop_prefix_cmd = r"""
    set -e
    ids=$(docker ps -q --filter "name=^ragflow_compose-" || true)
    if [ -n "$ids" ]; then
      docker stop $ids 2>&1 || true
    fi
    """.strip()
        _, out3 = self.ssh_executor.execute(stop_prefix_cmd)
        if (out3 or "").strip():
            self.append_restore_log(f"  {out3.strip()}")

    # Verify stopped (strict)
    self.append_restore_log(f"  [VERIFY] 校验容器已停止（超时 {timeout_s}s）...")
    deadline = time.time() + timeout_s
    last_running = ""
    while time.time() < deadline:
        check_cmd = r"""
    set -e
    running_ids=$(
      (
docker ps -q --filter "name=^ragflowauth-backend$" || true
docker ps -q --filter "name=^ragflowauth-frontend$" || true
docker ps -q --filter "name=^ragflow_compose-" || true
      ) | sort -u
    )
    if [ -n "$running_ids" ]; then
      echo "$running_ids"
      exit 2
    fi
    echo "STOPPED"
    """.strip()
        okc, outc = self.ssh_executor.execute(check_cmd)
        text = (outc or "").strip()
        if okc and text.endswith("STOPPED"):
            self.append_restore_log("  ✅ 校验通过：相关容器已停止")
            return
        last_running = text
        time.sleep(3)

    # Still running: provide actionable output and abort.
    okps, ps_out = self.ssh_executor.execute(
        "docker ps -a --format '{{.Names}}\\t{{.Image}}\\t{{.Status}}' | grep -E '^(ragflowauth-|ragflow_compose-)' 2>&1 || true"
    )
    self.append_restore_log("  ❌ 校验失败：容器可能仍在运行，已中止还原以避免索引/数据不一致。")
    if okps and (ps_out or "").strip():
        self.append_restore_log("  [DEBUG] docker ps -a（相关容器）:")
        self.append_restore_log(ps_out.strip())
    if last_running:
        self.append_restore_log("  [DEBUG] 最近一次检测到仍在运行的容器名:")
        self.append_restore_log(last_running)
    raise Exception("停止服务未完成：检测到相关容器仍在运行（请先确认已停止后再重试）")
