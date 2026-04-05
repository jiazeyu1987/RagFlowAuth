from ._shared import (
    _tool_mod,
    TEXT_ERROR_TITLE,
    TEXT_SUCCESS_TITLE,
    TEXT_MOUNT_HEADER,
    TEXT_SEPARATOR,
    TEXT_STATUS_MOUNTING,
    TEXT_STATUS_MOUNT_OK,
    TEXT_STATUS_MOUNT_FAILED,
    TEXT_NEED_SERVER_CONFIG,
)


def mount_windows_share(app, *args, **kwargs):
    return mount_windows_share_impl(app, *args, **kwargs)


def mount_windows_share_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if not app.update_ssh_executor():
        app.show_text_window(TEXT_ERROR_TITLE, TEXT_NEED_SERVER_CONFIG)
        return

    host = tool_mod.DEFAULT_WINDOWS_SHARE_HOST
    share = tool_mod.DEFAULT_WINDOWS_SHARE_NAME
    user = tool_mod.DEFAULT_WINDOWS_SHARE_USERNAME

    if host == app.config.ip:
        tool_mod.messagebox.showerror(
            TEXT_ERROR_TITLE,
            (
                f"Windows \u5171\u4eab IP \u4e0d\u80fd\u7b49\u4e8e\u670d\u52a1\u5668 IP\uff08{app.config.ip}\uff09\u3002\n"
                "\u5f53\u524d\u4e3a\u56fa\u5b9a\u914d\u7f6e\u6a21\u5f0f\uff0c\u8bf7\u4fee\u6539 ~/.ragflowauth_tool_config.txt \u4e2d WIN_SHARE_HOST\u3002"
            ),
        )
        return

    print(f"\n{TEXT_SEPARATOR}", flush=True)
    print(TEXT_MOUNT_HEADER, flush=True)
    print(f"[MOUNT] \u670d\u52a1\u5668: {app.config.user}@{app.config.ip}", flush=True)
    print(f"[MOUNT] Windows \u5171\u4eab: //{host}/{share}", flush=True)
    print(f"[MOUNT] \u5171\u4eab\u7528\u6237: {user}", flush=True)
    print(f"[MOUNT] \u6302\u8f7d\u70b9: {tool_mod.MOUNT_POINT}", flush=True)
    print(f"[MOUNT] \u76ee\u6807\u76ee\u5f55: {tool_mod.REPLICA_TARGET_DIR}", flush=True)
    print(f"{TEXT_SEPARATOR}\n", flush=True)

    def do_mount():
        try:
            app.status_bar.config(text=TEXT_STATUS_MOUNTING)
            app.root.update()

            result = tool_mod.feature_mount_windows_share(server_host=app.config.ip, server_user=app.config.user)
            log_content = result.log_content or result.stderr or ""

            if result.ok:
                print("[MOUNT] \u2713 \u6302\u8f7d\u6210\u529f", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_MOUNT_OK))
                app.root.after(
                    0,
                    lambda: app.show_text_window(
                        TEXT_SUCCESS_TITLE,
                        f"[GREEN]Windows \u5171\u4eab\u6302\u8f7d\u6210\u529f\uff01[/GREEN]\n\n{log_content}",
                    ),
                )
            else:
                print(f"[MOUNT] \u2717 \u6302\u8f7d\u5931\u8d25\n{result.stderr}", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_MOUNT_FAILED))
                app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u6302\u8f7d\u5931\u8d25[/RED]\n\n{log_content}"))

        except Exception as exc:
            print(f"[MOUNT] ERROR: {exc}", flush=True)
            app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u6302\u8f7d\u8fc7\u7a0b\u51fa\u9519:\n\n{str(exc)}[/RED]"))
            app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_MOUNT_FAILED))

    app.task_runner.run(name="mount_windows_share", fn=do_mount)

