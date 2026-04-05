from ._shared import (
    _tool_mod,
    TEXT_COUNT_SUFFIX,
    TEXT_LOADING_FILE_LIST,
    TEXT_LOADING_REPLICA_BACKUPS,
    TEXT_REPLICA_STATUS_PARTIAL,
)


def refresh_backup_files(app, *args, **kwargs):
    return refresh_backup_files_impl(app, *args, **kwargs)


def refresh_backup_files_impl(app, *args, **kwargs):
    if hasattr(app, "backup_files_status"):
        app.backup_files_status.config(text=TEXT_LOADING_FILE_LIST)
    app.root.update()

    app.update_ssh_executor()

    def load_files():
        left_files = app._get_backup_files("/opt/ragflowauth/data/backups/")
        right_files = app._get_backup_files("/opt/ragflowauth/backups/")
        app.root.after(0, lambda: app._update_file_trees(left_files, right_files))

    app.task_runner.run(name="refresh_backup_files", fn=load_files)


def refresh_replica_backups(app, *args, **kwargs):
    return refresh_replica_backups_impl(app, *args, **kwargs)


def refresh_replica_backups_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if hasattr(app, "replica_status"):
        app.replica_status.config(text=TEXT_LOADING_REPLICA_BACKUPS)
    app.root.update()

    def worker():
        test_res = tool_mod.feature_list_replica_backup_dirs(server_ip=tool_mod.TEST_SERVER_IP, server_user="root")
        prod_res = tool_mod.feature_list_replica_backup_dirs(server_ip=tool_mod.PROD_SERVER_IP, server_user="root")

        def apply():
            for tree in (getattr(app, "test_replica_tree", None), getattr(app, "prod_replica_tree", None)):
                if tree is None:
                    continue
                for iid in tree.get_children():
                    tree.delete(iid)

            if getattr(app, "test_replica_tree", None) is not None:
                for name in test_res.names:
                    app.test_replica_tree.insert("", tool_mod.tk.END, values=(name,))
                if hasattr(app, "test_replica_count"):
                    app.test_replica_count.config(text=f"{len(test_res.names)} {TEXT_COUNT_SUFFIX}")

            if getattr(app, "prod_replica_tree", None) is not None:
                for name in prod_res.names:
                    app.prod_replica_tree.insert("", tool_mod.tk.END, values=(name,))
                if hasattr(app, "prod_replica_count"):
                    app.prod_replica_count.config(text=f"{len(prod_res.names)} {TEXT_COUNT_SUFFIX}")

            if hasattr(app, "replica_status"):
                app.replica_status.config(
                    text=(
                        f"\u6d4b\u8bd5: {len(test_res.names)} {TEXT_COUNT_SUFFIX}\uff1b\u6b63\u5f0f: {len(prod_res.names)} {TEXT_COUNT_SUFFIX}"
                        + (TEXT_REPLICA_STATUS_PARTIAL if (not test_res.ok or not prod_res.ok) else "")
                    )
                )

        app.root.after(0, apply)

    app.task_runner.run(name="refresh_replica_backups", fn=worker)

