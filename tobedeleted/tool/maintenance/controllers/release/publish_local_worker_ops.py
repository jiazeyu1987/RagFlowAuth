from .publish_local_outcome_ops import (
    handle_publish_local_failed,
    handle_publish_local_success,
)
from .publish_local_ui_ops import (
    build_release_local_ui_logger,
    render_test_versions,
)


def run_publish_local_to_test_worker(
    app,
    *,
    tk,
    log_to_file,
    test_server_ip,
    feature_publish_from_local_to_test,
    want_sync_data,
    selected_pack,
):
    try:
        _prepare_publish_local_worker(app, tk=tk, log_to_file=log_to_file)
        ui_log = build_release_local_ui_logger(app, tk=tk)
        ui_log("[START] 发布本机 -> 测试：开始执行（可能需要较长时间，请勿关闭工具）")

        # Guardrail: ensure each environment reads its own RAGFlow.
        app._guard_ragflow_base_url(role="local", stage="LOCAL->TEST PRE")
        app._guard_ragflow_base_url(role="test", stage="LOCAL->TEST PRE")
        try:
            app.root.after(0, app.refresh_ragflow_base_urls)
        except Exception:
            pass

        result = feature_publish_from_local_to_test(version=app._release_version_arg(), ui_log=ui_log)
        render_test_versions(app, result=result, tk=tk)

        if result.ok:
            handle_publish_local_success(
                app,
                result=result,
                log_to_file=log_to_file,
                test_server_ip=test_server_ip,
                ui_log=ui_log,
                want_sync_data=want_sync_data,
                selected_pack=selected_pack,
            )
        else:
            handle_publish_local_failed(app, result=result, log_to_file=log_to_file, ui_log=ui_log)
    except Exception as e:
        if hasattr(app, "release_local_log_text"):
            app.release_local_log_text.insert(tk.END, f"[ERROR] {e}\n")
        log_to_file(f"[Release] Publish local->test exception: {e}", "ERROR")
        if hasattr(app, "status_bar"):
            app.status_bar.config(text="发布本机->测试：失败")


def _prepare_publish_local_worker(app, *, tk, log_to_file):
    if hasattr(app, "release_local_log_text"):
        app.release_local_log_text.delete("1.0", tk.END)
    if hasattr(app, "status_bar"):
        app.status_bar.config(text="发布本机->测试中...")
    log_to_file("[Release] Start publish local->test", "INFO")
