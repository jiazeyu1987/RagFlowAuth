from ._shared import (
    _tool_mod,
    TEXT_ERROR_TITLE,
    TEXT_MOUNT_STATUS_CHECK_TITLE,
    TEXT_CHECK_HEADER,
    TEXT_SEPARATOR,
    TEXT_STATUS_CHECKING,
    TEXT_STATUS_CHECK_OK,
    TEXT_STATUS_CHECK_FAILED,
    TEXT_NEED_SERVER_CONFIG,
)


def check_mount_status(app, *args, **kwargs):
    return check_mount_status_impl(app, *args, **kwargs)


def check_mount_status_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if not app.update_ssh_executor():
        app.show_text_window(TEXT_ERROR_TITLE, TEXT_NEED_SERVER_CONFIG)
        return

    print(f"\n{TEXT_SEPARATOR}", flush=True)
    print(TEXT_CHECK_HEADER, flush=True)
    print(f"[CHECK] \u670d\u52a1\u5668 IP: {app.config.ip}", flush=True)
    print(f"[CHECK] \u670d\u52a1\u5668\u7528\u6237: {app.config.user}", flush=True)
    print(f"{TEXT_SEPARATOR}\n", flush=True)

    def do_check():
        try:
            app.status_bar.config(text=TEXT_STATUS_CHECKING)
            app.root.update()

            result = tool_mod.feature_check_mount_status(server_host=app.config.ip, server_user=app.config.user)
            log_content = result.log_content or result.stderr or ""

            status_line = ""
            lines = log_content.split("\n")
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if "[Summary] Mount Status: Mounted" in line:
                    status_line = "[GREEN]\u6302\u8f7d\u72b6\u6001: \u5df2\u8fde\u63a5 (Mounted)[/GREEN]\n\n"
                    break
                if "[Summary] Mount Status: Not Mounted" in line:
                    status_line = "[RED]\u6302\u8f7d\u72b6\u6001: \u672a\u8fde\u63a5 (Not Mounted)[/RED]\n\n"
                    break

            if not status_line:
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    if "Status: Mounted (OK)" in line:
                        status_line = "[GREEN]\u6302\u8f7d\u72b6\u6001: \u5df2\u8fde\u63a5 (Mounted)[/GREEN]\n\n"
                        break
                    if "Status: Not Mounted" in line:
                        status_line = "[RED]\u6302\u8f7d\u72b6\u6001: \u672a\u8fde\u63a5 (Not Mounted)[/RED]\n\n"
                        break

            if status_line:
                log_content = status_line + log_content

            if result.returncode == 0:
                print("[CHECK] \u2713 \u68c0\u67e5\u5b8c\u6210", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_CHECK_OK))
                app.root.after(0, lambda: app.show_text_window(TEXT_MOUNT_STATUS_CHECK_TITLE, log_content))
            else:
                print(f"[CHECK] \u2717 \u68c0\u67e5\u5931\u8d25\n{result.stderr}", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_CHECK_FAILED))
                app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u68c0\u67e5\u5931\u8d25[/RED]\n\n{log_content}"))

        except Exception as exc:
            print(f"[CHECK] ERROR: {exc}", flush=True)
            app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u68c0\u67e5\u8fc7\u7a0b\u51fa\u9519:\n\n{str(exc)}[/RED]"))
            app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_CHECK_FAILED))

    app.task_runner.run(name="check_windows_share_mount", fn=do_check)

