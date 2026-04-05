from ._shared import _tool_mod


def refresh_admin_tabs_impl(app) -> None:
    self = app
    if self._is_admin_tab_user():
        if self.nas_tab is None:
            self.create_nas_tab()
    elif self.nas_tab is not None:
        try:
            self.notebook.forget(self.nas_tab)
        finally:
            self.nas_tab.destroy()
            self.nas_tab = None
            self.nas_tab_controller = None

