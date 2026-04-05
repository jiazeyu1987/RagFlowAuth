from pathlib import Path

from ._shared import _tool_mod

TEXT_LOCAL_BACKUP_AVAILABLE = "Available local backup packages: {count}"
TEXT_LOCAL_BACKUP_NOT_FOUND = "No local backup package found in: {root_dir}"
TEXT_LOCAL_BACKUP_REFRESH_FAILED = "Refresh local backup list failed: {error}"


def refresh_release_local_backup_list(app, *args, **kwargs):
    return refresh_release_local_backup_list_impl(app, *args, **kwargs)


def refresh_release_local_backup_list_impl(app, *args, **kwargs):
    """Refresh local backup catalog for the LOCAL -> TEST (sync data) flow."""
    tool_mod = _tool_mod()
    _ = args, kwargs

    try:
        root_dir = Path(r"D:\datas\RagflowAuth")
        entries = tool_mod.feature_list_local_backups(root_dir)

        app.release_local_backup_map = {}
        values = []
        for entry in entries:
            disp = f"{entry.label}  ({entry.path.name})"
            values.append(disp)
            app.release_local_backup_map[disp] = entry.path

        if hasattr(app, "release_local_backup_combo"):
            app.release_local_backup_combo["values"] = values

        if values:
            _set_default_local_backup_value_if_needed(app, values=values)
            if hasattr(app, "release_local_backup_note"):
                app.release_local_backup_note.config(
                    text=TEXT_LOCAL_BACKUP_AVAILABLE.format(count=len(values)),
                    foreground="gray",
                )
        else:
            if hasattr(app, "release_local_backup_var"):
                app.release_local_backup_var.set("")
            if hasattr(app, "release_local_backup_note"):
                app.release_local_backup_note.config(
                    text=TEXT_LOCAL_BACKUP_NOT_FOUND.format(root_dir=root_dir),
                    foreground="red",
                )
    except Exception as e:
        tool_mod.log_to_file(f"[Release] refresh local backup list failed: {e}", "ERROR")
        if hasattr(app, "release_local_backup_note"):
            app.release_local_backup_note.config(
                text=TEXT_LOCAL_BACKUP_REFRESH_FAILED.format(error=e),
                foreground="red",
            )


def _set_default_local_backup_value_if_needed(app, *, values):
    current = ""
    try:
        current = str(getattr(app, "release_local_backup_var", None).get() if hasattr(app, "release_local_backup_var") else "")
    except Exception:
        current = ""
    if (not current) or (current not in app.release_local_backup_map):
        if hasattr(app, "release_local_backup_var"):
            app.release_local_backup_var.set(values[0])
