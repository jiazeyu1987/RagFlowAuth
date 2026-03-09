from __future__ import annotations


class RagflowAuthToolRuntimeDelegateMixin:
    def on_environment_changed(self, event=None):
        from tool.maintenance.controllers.environment_controller import on_environment_changed_impl

        return on_environment_changed_impl(self, event)

    def _init_field_states(self):
        from tool.maintenance.controllers.environment_controller import init_field_states_impl

        return init_field_states_impl(self)

    def save_config(self):
        from tool.maintenance.controllers.environment_controller import save_config_impl

        return save_config_impl(self)

    def test_connection(self):
        from tool.maintenance.controllers.runtime_controller import test_connection_impl

        return test_connection_impl(self)

    def update_ssh_executor(self):
        from tool.maintenance.controllers.runtime_controller import update_ssh_executor_impl

        return update_ssh_executor_impl(self)

    def execute_ssh_command(self, command):
        from tool.maintenance.controllers.runtime_controller import execute_ssh_command_impl

        return execute_ssh_command_impl(self, command)

    def run_quick_deploy(self, *args, **kwargs):
        from tool.maintenance.controllers.deploy_controller import run_quick_deploy as controller_run_quick_deploy

        return controller_run_quick_deploy(self, *args, **kwargs)

    def _run_quick_deploy_impl(self):
        from tool.maintenance.controllers.deploy_controller import run_quick_deploy_impl as controller_run_quick_deploy_impl

        return controller_run_quick_deploy_impl(self)
    

    def cleanup_docker_images(self, *args, **kwargs):
        from tool.maintenance.controllers.deploy_controller import cleanup_docker_images as controller_cleanup_docker_images

        return controller_cleanup_docker_images(self, *args, **kwargs)

    def _cleanup_docker_images_impl(self):
        from tool.maintenance.controllers.deploy_controller import cleanup_docker_images_impl as controller_cleanup_docker_images_impl

        return controller_cleanup_docker_images_impl(self)
    

    def show_containers_with_mounts(self, *args, **kwargs):
        from tool.maintenance.controllers.deploy_controller import show_containers_with_mounts as controller_show_containers_with_mounts

        return controller_show_containers_with_mounts(self, *args, **kwargs)

    def _show_containers_with_mounts_impl(self):
        from tool.maintenance.controllers.deploy_controller import show_containers_with_mounts_impl as controller_show_containers_with_mounts_impl

        return controller_show_containers_with_mounts_impl(self)
    

    def show_result_window(self, title, content):
        from tool.maintenance.controllers.ui_window_controller import show_result_window_impl

        return show_result_window_impl(self, title, content)

    def open_frontend(self):
        from tool.maintenance.controllers.environment_controller import open_frontend_impl

        return open_frontend_impl(self)

    def open_portainer(self):
        from tool.maintenance.controllers.environment_controller import open_portainer_impl

        return open_portainer_impl(self)

    def open_web_console(self):
        from tool.maintenance.controllers.environment_controller import open_web_console_impl

        return open_web_console_impl(self)

    def open_custom_url(self):
        from tool.maintenance.controllers.environment_controller import open_custom_url_impl

        return open_custom_url_impl(self)

    def open_log_window(self, command):
        from tool.maintenance.controllers.runtime_controller import open_log_window_impl

        return open_log_window_impl(self, command)
