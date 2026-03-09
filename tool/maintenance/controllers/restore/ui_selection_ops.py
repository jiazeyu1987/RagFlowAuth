from ._shared import _tool_mod


def on_restore_backup_selected(app, _event=None):
    return on_restore_backup_selected_impl(app, _event=_event)


def on_restore_backup_selected_impl(app, _event=None):
    tool_mod = _tool_mod()
    path_cls = tool_mod.Path
    log_to_file = tool_mod.log_to_file

    _ = _event
    sel = app.restore_tree.selection()
    if not sel:
        return
    path = app.restore_backup_map.get(sel[0])
    if not path:
        return

    app.selected_restore_folder = path_cls(path)
    log_to_file(f"[RESTORE] Selected backup folder: {app.selected_restore_folder}")
    app.validate_restore_folder()
