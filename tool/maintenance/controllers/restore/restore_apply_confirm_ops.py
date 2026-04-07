def confirm_restore_plan(app, *, messagebox, log_to_file):
    restore_items = ["RagflowAuth 数据"]
    if app.restore_images_exists:
        restore_items.append("Docker 镜像")
    if app.restore_volumes_exists:
        restore_items.append("RAGFlow 数据 (volumes)")

    restore_type = " 和 ".join(restore_items)
    confirmed = messagebox.askyesno(
        "确认还原",
        f"即将还原 {restore_type} 到服务器\n\n"
        f"源文件夹: {app.selected_restore_folder}\n"
        f"目标服务器(固定): {app.restore_target_ip}\n\n"
        f"⚠️  警告：这将覆盖服务器上的现有数据！\n\n"
        f"是否继续？",
    )
    if not confirmed:
        log_to_file("[RESTORE] 用户取消还原操作")
        return None

    # 记录还原开始
    log_to_file("[RESTORE] 用户确认还原操作")
    log_to_file(f"[RESTORE] 源文件夹: {app.selected_restore_folder}")
    log_to_file(f"[RESTORE] 目标服务器: {app.restore_target_user}@{app.restore_target_ip}")
    log_to_file(f"[RESTORE] 还原内容: {restore_type}")
    return restore_type
