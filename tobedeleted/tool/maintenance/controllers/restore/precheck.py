from ._shared import (
    _tool_mod,
    TEXT_RESTORE_FOLDER_NOT_EXISTS,
    TEXT_MISSING_AUTH_DB,
    TEXT_FOUND_DB,
    TEXT_FOUND_IMAGES,
    TEXT_IMAGES_NOT_FOUND,
    TEXT_FOUND_VOLUMES,
    TEXT_VOLUMES_NOT_FOUND,
    TEXT_LOG_PREFIX,
)

def validate_restore_folder(app, *args, **kwargs):
    return validate_restore_folder_impl(app, *args, **kwargs)

def validate_restore_folder_impl(app, *args, **kwargs):
    tool_mod = _tool_mod()

    if not app.selected_restore_folder or not app.selected_restore_folder.exists():
        app.restore_info_label.config(text=TEXT_RESTORE_FOLDER_NOT_EXISTS, foreground="red")
        app.restore_btn.config(state=tool_mod.tk.DISABLED)
        if hasattr(app, "restore_start_btn"):
            app.restore_start_btn.config(state=tool_mod.tk.DISABLED)
        return

    auth_db = app.selected_restore_folder / "auth.db"
    images_tar = app.selected_restore_folder / "images.tar"
    volumes_dir = app.selected_restore_folder / "volumes"

    info_text = []
    is_valid = True

    if not auth_db.exists():
        info_text.append(TEXT_MISSING_AUTH_DB)
        is_valid = False
    else:
        info_text.append(TEXT_FOUND_DB.format(size_mb=auth_db.stat().st_size / 1024 / 1024))

    if images_tar.exists():
        size_mb = images_tar.stat().st_size / 1024 / 1024
        info_text.append(TEXT_FOUND_IMAGES.format(size_mb=size_mb))
        app.restore_images_exists = True
    else:
        info_text.append(TEXT_IMAGES_NOT_FOUND)
        app.restore_images_exists = False

    if volumes_dir.exists() and volumes_dir.is_dir():
        volume_items = list(volumes_dir.rglob("*"))
        info_text.append(TEXT_FOUND_VOLUMES.format(count=len(volume_items)))
        app.restore_volumes_exists = True
    else:
        info_text.append(TEXT_VOLUMES_NOT_FOUND)
        app.restore_volumes_exists = False

    app.restore_info_label.config(text="\n".join(info_text), foreground="blue" if is_valid else "red")

    tool_mod.log_to_file(TEXT_LOG_PREFIX + "\n".join(info_text))

    if is_valid and auth_db.exists():
        app.restore_btn.config(state=tool_mod.tk.NORMAL)
        if hasattr(app, "restore_start_btn"):
            app.restore_start_btn.config(state=tool_mod.tk.NORMAL)
    else:
        app.restore_btn.config(state=tool_mod.tk.DISABLED)
        if hasattr(app, "restore_start_btn"):
            app.restore_start_btn.config(state=tool_mod.tk.DISABLED)
