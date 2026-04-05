from ._shared import TEXT_HINT_TITLE, TEXT_RESTORE_FIXED_DIR, _tool_mod


def select_restore_folder(app, *args, **kwargs):
    return select_restore_folder_impl(app, *args, **kwargs)


def select_restore_folder_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()
    tool_mod.messagebox.showinfo(TEXT_HINT_TITLE, TEXT_RESTORE_FIXED_DIR)
    app.refresh_local_restore_list()


def refresh_local_restore_list(app):
    return refresh_local_restore_list_impl(app)


def refresh_local_restore_list_impl(app):
    tool_mod = _tool_mod()
    path_cls = tool_mod.Path
    feature_list_local_backups = tool_mod.feature_list_local_backups
    tk = tool_mod.tk

    root_dir = path_cls(r"D:\datas\RagflowAuth")
    entries = feature_list_local_backups(root_dir)

    app.restore_backup_map = {}
    if hasattr(app, "restore_tree"):
        for item in app.restore_tree.get_children():
            app.restore_tree.delete(item)

        for entry in entries:
            has_images = "Yes" if (entry.path / "images.tar").exists() else "No"
            iid = app.restore_tree.insert("", tk.END, values=(entry.label, has_images, entry.path.name))
            app.restore_backup_map[iid] = entry.path

    if not entries:
        app.restore_info_label.config(
            text=f"No valid backup folders found (auth.db required): {root_dir}",
            foreground="red",
        )
        app.restore_btn.config(state=tk.DISABLED)
        if hasattr(app, "restore_start_btn"):
            app.restore_start_btn.config(state=tk.DISABLED)
