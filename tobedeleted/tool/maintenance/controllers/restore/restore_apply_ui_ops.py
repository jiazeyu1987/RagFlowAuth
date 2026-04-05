def prepare_restore_ui_before_run(app, *, tk):
    # 禁用按钮
    app.restore_btn.config(state=tk.DISABLED)
    if hasattr(app, "restore_start_btn"):
        app.restore_start_btn.config(state=tk.DISABLED)
    app.restore_output.config(state=tk.NORMAL)
    app.restore_output.delete(1.0, tk.END)
    app.restore_output.config(state=tk.DISABLED)

    # 启动进度条
    app.restore_progress.start(10)
    app.update_restore_status("正在准备还原...")
