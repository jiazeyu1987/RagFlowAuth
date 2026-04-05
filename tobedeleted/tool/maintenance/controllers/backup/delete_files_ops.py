from ._shared import (
    _tool_mod,
    TEXT_DELETE_FILE_CONFIRM_TITLE,
    TEXT_HINT_TITLE,
    TEXT_SELECT_BACKUP_FILE_FIRST,
)


def delete_selected_backup_files(app, *args, **kwargs):
    return delete_selected_backup_files_impl(app, *args, **kwargs)


def delete_selected_backup_files_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    left_selected = app.left_tree.selection()
    right_selected = app.right_tree.selection()

    if not left_selected and not right_selected:
        tool_mod.messagebox.showwarning(TEXT_HINT_TITLE, TEXT_SELECT_BACKUP_FILE_FIRST)
        return

    files_to_delete = []

    for item in left_selected:
        values = app.left_tree.item(item, "values")
        file_name = values[0]
        files_to_delete.append(("/opt/ragflowauth/data/backups/", file_name))

    for item in right_selected:
        values = app.right_tree.item(item, "values")
        file_name = values[0]
        files_to_delete.append(("/opt/ragflowauth/backups/", file_name))

    file_list = "\n".join([f"  {path}{name}" for path, name in files_to_delete])
    confirm = tool_mod.messagebox.askyesno(
        TEXT_DELETE_FILE_CONFIRM_TITLE,
        f"\u786e\u5b9a\u8981\u5220\u9664\u4ee5\u4e0b {len(files_to_delete)} \u4e2a\u5907\u4efd\u5417\uff1f\n\n{file_list}",
    )
    if not confirm:
        return

    app.backup_files_status.config(text=f"\u6b63\u5728\u5220\u9664 {len(files_to_delete)} \u4e2a\u6587\u4ef6...")
    app.root.update()

    def delete_files():
        deleted = []
        failed = []

        for base_path, file_name in files_to_delete:
            full_path = f"{base_path}{file_name}"
            cmd = f"rm -rf {full_path}"
            success, _ = app.ssh_executor.execute(cmd)

            if success:
                deleted.append(file_name)
            else:
                failed.append(file_name)

        app.root.after(0, lambda: app._delete_complete(deleted, failed))

    app.task_runner.run(name="backup_files_delete", fn=delete_files)
