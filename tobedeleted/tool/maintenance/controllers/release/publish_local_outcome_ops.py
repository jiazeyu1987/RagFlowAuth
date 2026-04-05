from .worker_shared_ops import (
    log_result_lines,
    request_base_url_refresh,
)


def handle_publish_local_success(app, *, result, log_to_file, test_server_ip, ui_log, want_sync_data, selected_pack):
    app._record_release_event(
        event="LOCAL->TEST",
        server_ip=test_server_ip,
        version=app._extract_version_from_release_log(result.log) or (app._release_version_arg() or ""),
        details=app._format_version_info(result.version_after) if result.version_after else "",
    )
    log_result_lines(
        log_to_file=log_to_file,
        prefix="[ReleaseFlow]",
        result_log=result.log,
        level="INFO",
    )
    log_to_file("[Release] Publish local->test succeeded", "INFO")
    ui_log("[DONE] 发布本机 -> 测试：成功")
    if hasattr(app, "status_bar"):
        app.status_bar.config(text="发布本机->测试：成功")

    # Optional: sync latest local backup data (auth.db + RAGFlow volumes) to TEST.
    if want_sync_data:
        run_optional_local_sync(
            app,
            log_to_file=log_to_file,
            ui_log=ui_log,
            selected_pack=selected_pack,
        )

    # Post-check (defensive): publish/sync may overwrite config; enforce again.
    app._guard_ragflow_base_url(role="test", stage="LOCAL->TEST POST")
    request_base_url_refresh(app)


def run_optional_local_sync(app, *, log_to_file, ui_log, selected_pack):
    ui_log("")
    ui_log("[SYNC] 发布成功，开始同步本机最新备份到测试（auth.db + RAGFlow volumes）...")
    try:
        app._sync_local_backup_to_test(pack_dir=selected_pack, ui_log=ui_log)
        ui_log("[SYNC] 同步完成")
        if hasattr(app, "status_bar"):
            app.root.after(0, lambda: app.status_bar.config(text="发布本机->测试：成功（数据已同步）"))
    except Exception as e:
        ui_log(f"[SYNC] [ERROR] 同步失败: {e}")
        log_to_file(f"[Release] local->test sync data failed: {e}", "ERROR")
        if hasattr(app, "status_bar"):
            app.root.after(0, lambda: app.status_bar.config(text="发布本机->测试：成功（数据同步失败）"))


def handle_publish_local_failed(app, *, result, log_to_file, ui_log):
    log_result_lines(
        log_to_file=log_to_file,
        prefix="[ReleaseFlow]",
        result_log=result.log,
        level="ERROR",
    )
    log_to_file("[Release] Publish local->test failed", "ERROR")
    ui_log("[DONE] 发布本机 -> 测试：失败（请查看上方日志与 tool_log.log）")
    if hasattr(app, "status_bar"):
        app.status_bar.config(text="发布本机->测试：失败")
