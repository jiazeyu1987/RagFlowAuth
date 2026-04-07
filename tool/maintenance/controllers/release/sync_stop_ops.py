def stop_services_on_test(*, service_controller_cls, ssh, ui_log):
    # 1) Stop services strictly (ragflowauth + ragflow stack), and verify clean stop.
    ui_log("[SYNC] [1/5] Stop services on TEST (strict)")
    controller = service_controller_cls(
        exec_fn=lambda c, t: ssh.execute(c, timeout_seconds=t),
        log=lambda m: ui_log(f"[SYNC] {m}"),
    )
    stop_res = controller.stop_and_verify(app_dir="/opt/ragflowauth", mode="down", timeout_s=90, who="TEST")
    if not stop_res.ok:
        raise RuntimeError(f"停止服务未完成：{stop_res.error}")
