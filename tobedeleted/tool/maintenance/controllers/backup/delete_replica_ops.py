from ._shared import (
    _tool_mod,
    TEXT_CONFIRM_TITLE,
    TEXT_DELETE_REPLICA_RESULT_TITLE,
    TEXT_HINT_TITLE,
    TEXT_REPLICA_NAME_PARSE_FAILED,
    TEXT_SELECT_REPLICA_BACKUP_FIRST,
)


def delete_selected_replica_backup(app, *args, **kwargs):
    return delete_selected_replica_backup_impl(app, *args, **kwargs)


def delete_selected_replica_backup_impl(app, which: str, *args, **kwargs):
    tool_mod = _tool_mod()

    which = (which or "").strip().lower()
    if which not in ("test", "prod"):
        return

    server_ip = tool_mod.TEST_SERVER_IP if which == "test" else tool_mod.PROD_SERVER_IP
    tree = getattr(app, "test_replica_tree", None) if which == "test" else getattr(app, "prod_replica_tree", None)
    if tree is None:
        return

    sel = list(tree.selection())
    if not sel:
        tool_mod.messagebox.showwarning(TEXT_HINT_TITLE, TEXT_SELECT_REPLICA_BACKUP_FIRST)
        return

    names = []
    for iid in sel:
        vals = tree.item(iid, "values") or []
        if vals:
            names.append(str(vals[0]))

    if not names:
        tool_mod.messagebox.showwarning(TEXT_HINT_TITLE, TEXT_REPLICA_NAME_PARSE_FAILED)
        return

    confirm_msg = (
        f"\u5373\u5c06\u4ece {which.upper()} \u670d\u52a1\u5668\uff08{server_ip}\uff09\u5220\u9664 {len(names)} \u4e2a\u672c\u673a\u5907\u4efd\u76ee\u5f55\uff08/opt/ragflowauth/data/backups\uff09\uff1a\n\n"
        + "\n".join(names[:12])
        + ("\n..." if len(names) > 12 else "")
        + "\n\n\u5220\u9664\u540e\u4e0d\u53ef\u6062\u590d\uff0c\u786e\u5b9a\u7ee7\u7eed\u5417\uff1f"
    )
    confirm = tool_mod.messagebox.askyesno(TEXT_CONFIRM_TITLE, confirm_msg)
    if not confirm:
        return

    if hasattr(app, "replica_status"):
        app.replica_status.config(text=f"\u6b63\u5728\u5220\u9664 {which.upper()} \u9009\u4e2d\u5907\u4efd\u76ee\u5f55...")

    def worker():
        results = []
        for name in names:
            results.append(tool_mod.feature_delete_replica_backup_dir(server_ip=server_ip, server_user="root", name=name))

        def apply():
            ok_cnt = sum(1 for r in results if r.ok)
            fail_cnt = len(results) - ok_cnt
            log_lines = [f"[TARGET] {which.upper()} {server_ip}", ""]
            for r in results:
                log_lines.append(f"- {r.name}: {'OK' if r.ok else 'FAIL'} ({r.message})")

            app.show_text_window(TEXT_DELETE_REPLICA_RESULT_TITLE, "\n".join(log_lines))
            if hasattr(app, "replica_status"):
                app.replica_status.config(text=f"\u5220\u9664\u5b8c\u6210\uff1a\u6210\u529f {ok_cnt} \u4e2a\uff0c\u5931\u8d25 {fail_cnt} \u4e2a")
            app.refresh_replica_backups()

        app.root.after(0, apply)

    app.task_runner.run(name="delete_selected_replica_backup", fn=worker)
