def confirm_publish_test_to_prod(*, messagebox, test_server_ip, prod_server_ip):
    return messagebox.askyesno(
        "确认发布",
        f"确认要从测试服务器 {test_server_ip} 发布到正式服务器 {prod_server_ip} 吗？\n"
        "注意：这会重启正式环境容器，请在低峰期执行。",
    )
