from ._shared import (
    _tool_mod,
    TEXT_ERROR_TITLE,
    TEXT_MOUNT_SUCCESS_TITLE,
    TEXT_UNMOUNT_HEADER,
    TEXT_SEPARATOR,
    TEXT_STATUS_UNMOUNTING,
    TEXT_STATUS_UNMOUNT_OK,
    TEXT_STATUS_UNMOUNT_FAILED,
    TEXT_NEED_SERVER_CONFIG,
)


def unmount_windows_share(app, *args, **kwargs):
    return unmount_windows_share_impl(app, *args, **kwargs)


def unmount_windows_share_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if not app.update_ssh_executor():
        app.show_text_window(TEXT_ERROR_TITLE, TEXT_NEED_SERVER_CONFIG)
        return

    print(f"\n{TEXT_SEPARATOR}", flush=True)
    print(TEXT_UNMOUNT_HEADER, flush=True)
    print(f"[UNMOUNT] \u670d\u52a1\u5668: {app.config.user}@{app.config.ip}", flush=True)
    print(f"[UNMOUNT] \u6302\u8f7d\u70b9: {tool_mod.MOUNT_POINT}", flush=True)
    print(f"{TEXT_SEPARATOR}\n", flush=True)

    def do_unmount():
        try:
            app.status_bar.config(text=TEXT_STATUS_UNMOUNTING)
            app.root.update()

            result = tool_mod.feature_unmount_windows_share(server_host=app.config.ip, server_user=app.config.user)
            log_content = result.log_content or result.stderr or ""

            if result.ok:
                print("[UNMOUNT] \u2713 \u5378\u8f7d\u6210\u529f", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_UNMOUNT_OK))
                app.root.after(
                    0,
                    lambda: app.show_text_window(
                        TEXT_MOUNT_SUCCESS_TITLE,
                        f"[GREEN]Windows \u7f51\u7edc\u5171\u4eab\u5df2\u6210\u529f\u5378\u8f7d\uff01[/GREEN]\n\n{log_content}",
                    ),
                )
            else:
                print(f"[UNMOUNT] \u2717 \u5378\u8f7d\u5931\u8d25\n{result.stderr}", flush=True)
                app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_UNMOUNT_FAILED))
                app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u5378\u8f7d\u5931\u8d25[/RED]\n\n{log_content}"))

        except Exception as exc:
            print(f"[UNMOUNT] ERROR: {exc}", flush=True)
            app.root.after(0, lambda: app.show_text_window(TEXT_ERROR_TITLE, f"[RED]\u5378\u8f7d\u8fc7\u7a0b\u51fa\u9519:\n\n{str(exc)}[/RED]"))
            app.root.after(0, lambda: app.status_bar.config(text=TEXT_STATUS_UNMOUNT_FAILED))

    app.task_runner.run(name="unmount_windows_share", fn=do_unmount)

