def resolve_local_sync_selection(app):
    want_sync_data = bool(
        getattr(app, "release_local_sync_data_var", None).get() if hasattr(app, "release_local_sync_data_var") else False
    )

    selected_pack = None
    if want_sync_data:
        try:
            disp = str(
                getattr(app, "release_local_backup_var", None).get() if hasattr(app, "release_local_backup_var") else ""
            ).strip()
            mapping = getattr(app, "release_local_backup_map", None) or {}
            selected_pack = mapping.get(disp)
        except Exception:
            selected_pack = None

    return want_sync_data, selected_pack


def confirm_publish_local_to_test(*, messagebox, test_server_ip, want_sync_data, selected_pack):
    confirm_msg = (
        f"确认要从本机发布到测试服务器 {test_server_ip} 吗？\n"
        "注意：这会重启测试环境容器。\n"
    )
    if want_sync_data:
        chosen = str(selected_pack) if selected_pack else "（未选择：将自动使用最新备份）"
        confirm_msg += (
            "\n并且将执行【发布后同步数据到测试】（覆盖测试数据）：\n"
            "- auth.db\n"
            "- RAGFlow volumes（MySQL/MinIO/ES 等）\n"
            f"\n数据来源：{chosen}\n"
        )

    if not messagebox.askyesno("确认发布", confirm_msg):
        return False, want_sync_data

    if want_sync_data and (
        not messagebox.askyesno(
            "确认同步数据到测试",
            "再次确认：同步数据会覆盖【测试服务器】上的 auth.db 和 RAGFlow volumes。\n\n是否继续？",
        )
    ):
        want_sync_data = False

    return True, want_sync_data
