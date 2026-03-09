def ensure_restore_selection(app, *, log_to_file, messagebox):
    if app.selected_restore_folder:
        return True

    msg = "[ERROR] 请先选择备份文件夹"
    print(msg)
    log_to_file(msg, "ERROR")
    messagebox.showerror("错误", "请先选择备份文件夹")
    return False


def enforce_test_base_url_before_restore(app, *, test_server_ip, log_to_file, messagebox):
    # 防呆：还原前自动修正测试服务器 ragflow_config.json 的 base_url，避免误读生产知识库
    try:
        cfg_path = "/opt/ragflowauth/ragflow_config.json"
        cmd = (
            f"test -f {cfg_path} || (echo MISSING && exit 0); "
            f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
        )
        ok, out = app.ssh_executor.execute(cmd)
        base_url = (out or "").strip().splitlines()[-1].strip() if (out or "").strip() else ""
        if (not ok) or (not base_url) or (base_url == "MISSING"):
            messagebox.showerror(
                "还原前检查失败",
                f"无法读取测试服务器 ragflow_config.json 的 base_url。\n"
                f"服务器: {app.restore_target_ip}\n"
                f"文件: {cfg_path}\n"
                f"输出: {out}",
            )
            log_to_file(f"[RESTORE] [PRECHECK] failed to read base_url: {out}", "ERROR")
            return False

        desired = f"http://{test_server_ip}:9380"
        if desired not in base_url:
            app.append_restore_log(f"[PRECHECK] 检测到 base_url={base_url}，将自动修正为 {desired}")
            log_to_file(f"[RESTORE] [PRECHECK] rewriting base_url: {base_url} -> {desired}")

            # Backup then atomic rewrite (keep JSON formatting roughly intact)
            fix_cmd = (
                f"set -e; "
                f"cp -f {cfg_path} {cfg_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; "
                f"tmp=$(mktemp); "
                f"sed -E 's#(\"base_url\"[[:space:]]*:[[:space:]]*\")([^\\\"]+)(\")#\\1{desired}\\3#' {cfg_path} > $tmp; "
                f"mv -f $tmp {cfg_path}; "
                f"sed -n 's/.*\"base_url\"[[:space:]]*:[[:space:]]*\"\\([^\\\"]*\\)\".*/\\1/p' {cfg_path} | head -n 1"
            )
            ok2, out2 = app.ssh_executor.execute(fix_cmd)
            new_base = (out2 or "").strip().splitlines()[-1].strip() if (out2 or "").strip() else ""
            if (not ok2) or (desired not in new_base):
                messagebox.showerror(
                    "还原前自动修正失败",
                    f"已尝试将测试服务器 base_url 修正为 {desired}，但未成功。\n"
                    f"当前读取: {new_base or '(empty)'}\n\n"
                    f"输出: {out2}",
                )
                log_to_file(f"[RESTORE] [PRECHECK] rewrite failed: {out2}", "ERROR")
                return False
            app.append_restore_log(f"[PRECHECK] base_url 已修正: {new_base}")

        log_to_file(f"[RESTORE] [PRECHECK] ragflow base_url OK: {base_url}")
        return True
    except Exception as exc:
        log_to_file(f"[RESTORE] [PRECHECK] exception: {exc}", "ERROR")
        messagebox.showerror("还原前检查异常", str(exc))
        return False
