from .worker_shared_ops import (
    log_result_lines,
    request_base_url_refresh,
)


def run_publish_test_data_to_prod_worker(app, *, tk, log_to_file, prod_server_ip, feature_publish_data_from_test_to_prod):
    try:
        if hasattr(app, "release_data_log_text"):
            app.root.after(0, lambda: app.release_data_log_text.delete("1.0", tk.END))
        if hasattr(app, "status_bar"):
            app.status_bar.config(text="正在发布测试数据到正式...")
        log_to_file("[ReleaseData] Start publish test-data->prod", "INFO")

        ui_log = build_release_data_ui_logger(app, tk=tk)

        # Guardrail: enforce base_url isolation before data sync.
        app._guard_ragflow_base_url(role="test", stage="TEST->PROD(DATA) PRE", ui_log=ui_log)
        app._guard_ragflow_base_url(role="prod", stage="TEST->PROD(DATA) PRE", ui_log=ui_log)
        request_base_url_refresh(app)

        result = feature_publish_data_from_test_to_prod(version=app._release_version_arg(), log_cb=ui_log)

        # Post-check: enforce base_url after sync attempt.
        app._guard_ragflow_base_url(role="prod", stage="TEST->PROD(DATA) POST", ui_log=ui_log)
        request_base_url_refresh(app)

        if result.ok:
            app._record_release_event(
                event="TEST->PROD(DATA)",
                server_ip=prod_server_ip,
                version=app._extract_version_from_release_log(result.log) or (app._release_version_arg() or ""),
                details="sync auth.db + ragflow volumes",
            )
            log_result_lines(
                log_to_file=log_to_file,
                prefix="[ReleaseDataFlow]",
                result_log=result.log,
                level="INFO",
            )
            log_to_file("[ReleaseData] Publish succeeded", "INFO")
            if hasattr(app, "status_bar"):
                app.status_bar.config(text="数据发布：成功")
        else:
            log_result_lines(
                log_to_file=log_to_file,
                prefix="[ReleaseDataFlow]",
                result_log=result.log,
                level="ERROR",
            )
            log_to_file("[ReleaseData] Publish failed", "ERROR")
            if hasattr(app, "status_bar"):
                app.status_bar.config(text="数据发布：失败")
    except Exception as e:
        if hasattr(app, "release_data_log_text"):
            app.root.after(0, lambda: app.release_data_log_text.insert(tk.END, f"[ERROR] {e}\n"))
        log_to_file(f"[ReleaseData] Publish exception: {e}", "ERROR")
        if hasattr(app, "status_bar"):
            app.status_bar.config(text="数据发布：失败")


def build_release_data_ui_logger(app, *, tk):
    def ui_log(line: str) -> None:
        if not hasattr(app, "release_data_log_text"):
            return

        def _append() -> None:
            app.release_data_log_text.insert(tk.END, line + "\n")
            app.release_data_log_text.see(tk.END)

        app.root.after(0, _append)

    return ui_log
