def confirm_publish_test_data_to_prod(*, messagebox, test_server_ip, prod_server_ip):
    first = messagebox.askyesno(
        "确认数据发布（第 1 次确认）",
        f"即将把【测试服务器】数据发布到【正式服务器】。\n\n"
        f"测试: {test_server_ip}\n"
        f"正式: {prod_server_ip}\n\n"
        f"⚠️  警告：这会覆盖正式服务器上的 auth.db 和 RAGFlow volumes 数据！\n\n"
        f"是否继续？",
    )
    if not first:
        return False

    second = messagebox.askyesno(
        "确认数据发布（第 2 次确认）",
        "再次确认：你已理解此操作会覆盖生产数据，且无法自动回滚。\n\n是否继续？",
    )
    return bool(second)
