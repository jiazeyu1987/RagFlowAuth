from __future__ import annotations


class RagflowAuthToolRestoreDelegateMixin:
    def select_restore_folder(self, *args, **kwargs):
        from tool.maintenance.controllers.restore_controller import select_restore_folder as controller_select_restore_folder

        return controller_select_restore_folder(self, *args, **kwargs)

    def _select_restore_folder_impl(self):
        from tool.maintenance.controllers.restore_controller import select_restore_folder_impl as controller_select_restore_folder_impl

        return controller_select_restore_folder_impl(self)
    

    def validate_restore_folder(self, *args, **kwargs):
        from tool.maintenance.controllers.restore_controller import validate_restore_folder as controller_validate_restore_folder

        return controller_validate_restore_folder(self, *args, **kwargs)

    def _validate_restore_folder_impl(self):
        from tool.maintenance.controllers.restore_controller import validate_restore_folder_impl as controller_validate_restore_folder_impl

        return controller_validate_restore_folder_impl(self)
    
    def append_restore_log(self, text):
        from tool.maintenance.controllers.restore_controller import append_restore_log_impl as controller_append_restore_log_impl

        return controller_append_restore_log_impl(self, text)

    def update_restore_status(self, text):
        from tool.maintenance.controllers.restore_controller import update_restore_status_impl as controller_update_restore_status_impl

        return controller_update_restore_status_impl(self, text)

    def stop_restore_progress(self):
        from tool.maintenance.controllers.restore_controller import stop_restore_progress_impl as controller_stop_restore_progress_impl

        return controller_stop_restore_progress_impl(self)

    def restore_data(self, *args, **kwargs):
        from tool.maintenance.controllers.restore_controller import restore_data as controller_restore_data

        return controller_restore_data(self, *args, **kwargs)

    def _restore_data_impl(self):
        from tool.maintenance.controllers.restore_controller import restore_data_impl as controller_restore_data_impl

        return controller_restore_data_impl(self)
    

    def _execute_restore(self):
        from tool.maintenance.controllers.restore_controller import execute_restore_impl as controller_execute_restore_impl

        return controller_execute_restore_impl(self)
