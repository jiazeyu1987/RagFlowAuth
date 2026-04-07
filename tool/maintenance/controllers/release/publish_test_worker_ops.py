from .worker_shared_ops import (
    log_result_lines,
    request_base_url_refresh,
)


def run_publish_test_to_prod_worker(app, *, tk, log_to_file, prod_server_ip, feature_publish_from_test_to_prod):
    try:
        app.release_log_text.delete("1.0", tk.END)
        app.status_bar.config(text="发布中...")
        log_to_file("[Release] Start publish test->prod", "INFO")

        include_ragflow = bool(getattr(app, "release_include_ragflow_var", tk.BooleanVar(value=False)).get())
        # Guardrail: enforce base_url isolation before publish.
        app._guard_ragflow_base_url(role="test", stage="TEST->PROD(IMAGE) PRE")
        app._guard_ragflow_base_url(role="prod", stage="TEST->PROD(IMAGE) PRE")
        request_base_url_refresh(app)

        result = feature_publish_from_test_to_prod(
            version=app._release_version_arg(),
            include_ragflow_images=include_ragflow,
        )
        app.release_log_text.insert(tk.END, (result.log or "") + "\n")

        # Post-check: enforce PROD base_url after publish attempt (success or fail).
        app._guard_ragflow_base_url(role="prod", stage="TEST->PROD(IMAGE) POST")
        request_base_url_refresh(app)

        if result.ok:
            app._record_release_event(
                event="TEST->PROD(IMAGE)",
                server_ip=prod_server_ip,
                version=app._extract_version_from_release_log(result.log) or (app._release_version_arg() or ""),
                details=app._format_version_info(result.version_after) if result.version_after else "",
            )
            log_result_lines(
                log_to_file=log_to_file,
                prefix="[ReleaseFlow]",
                result_log=result.log,
                level="INFO",
            )
            log_to_file("[Release] Publish succeeded", "INFO")
            app.status_bar.config(text="发布：成功")
        else:
            log_result_lines(
                log_to_file=log_to_file,
                prefix="[ReleaseFlow]",
                result_log=result.log,
                level="ERROR",
            )
            log_to_file("[Release] Publish failed", "ERROR")
            app.status_bar.config(text="发布：失败")

        app.refresh_release_versions()
    except Exception as e:
        app.release_log_text.insert(tk.END, f"[ERROR] {e}\n")
        log_to_file(f"[Release] Publish exception: {e}", "ERROR")
        app.status_bar.config(text="发布：失败")
