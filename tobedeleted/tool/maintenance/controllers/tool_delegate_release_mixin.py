from __future__ import annotations

import tkinter as tk
from pathlib import Path


class RagflowAuthToolReleaseDelegateMixin:
    def deploy_onlyoffice_to_test(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import deploy_onlyoffice_to_test as controller_deploy_onlyoffice_to_test

        return controller_deploy_onlyoffice_to_test(self, *args, **kwargs)

    def _deploy_onlyoffice_to_test_impl(self):
        from tool.maintenance.controllers.release_controller import deploy_onlyoffice_to_test_impl as controller_deploy_onlyoffice_to_test_impl

        return controller_deploy_onlyoffice_to_test_impl(self)

    def deploy_onlyoffice_to_prod(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import deploy_onlyoffice_to_prod as controller_deploy_onlyoffice_to_prod

        return controller_deploy_onlyoffice_to_prod(self, *args, **kwargs)

    def _deploy_onlyoffice_to_prod_impl(self):
        from tool.maintenance.controllers.release_controller import deploy_onlyoffice_to_prod_impl as controller_deploy_onlyoffice_to_prod_impl

        return controller_deploy_onlyoffice_to_prod_impl(self)

    def _deploy_onlyoffice_to_server(self, *, server_ip: str, display_name: str) -> None:
        from tool.maintenance.controllers.release.helper_ops import deploy_onlyoffice_to_server

        return deploy_onlyoffice_to_server(self, server_ip=server_ip, display_name=display_name)

    def run_smoke_test(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import run_smoke_test as controller_run_smoke_test

        return controller_run_smoke_test(self, *args, **kwargs)

    def _run_smoke_test_impl(self, server_ip: str):
        from tool.maintenance.controllers.release_controller import run_smoke_test_impl as controller_run_smoke_test_impl

        return controller_run_smoke_test_impl(self, server_ip)

    def _set_smoke_output(self, text: str):
        try:
            self.smoke_output.delete("1.0", tk.END)
            self.smoke_output.insert(tk.END, text)
        except Exception:
            pass

    @staticmethod
    def _extract_version_from_release_log(text: str | None) -> str | None:
        from tool.maintenance.controllers.release.helper_ops import extract_version_from_release_log

        return extract_version_from_release_log(text)

    def _record_release_event(self, *, event: str, server_ip: str, version: str, details: str) -> None:
        from tool.maintenance.controllers.release.helper_ops import record_release_event

        return record_release_event(self, event=event, server_ip=server_ip, version=version, details=details)

    def _release_generate_version(self):
        from tool.maintenance.controllers.release.helper_ops import release_generate_version

        return release_generate_version(self)

    def _release_version_arg(self) -> str | None:
        from tool.maintenance.controllers.release.helper_ops import release_version_arg

        return release_version_arg(self)

    def _format_version_info(self, info) -> str:
        from tool.maintenance.controllers.release.helper_ops import format_version_info

        return format_version_info(info)

    def refresh_release_versions(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_release_versions as controller_refresh_release_versions

        return controller_refresh_release_versions(self, *args, **kwargs)

    def _refresh_release_versions_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_release_versions_impl as controller_refresh_release_versions_impl

        return controller_refresh_release_versions_impl(self)
    

    def refresh_ragflow_base_urls(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_ragflow_base_urls as controller_refresh_ragflow_base_urls

        return controller_refresh_ragflow_base_urls(self, *args, **kwargs)

    def _refresh_ragflow_base_urls_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_ragflow_base_urls_impl as controller_refresh_ragflow_base_urls_impl

        return controller_refresh_ragflow_base_urls_impl(self)
    

    def _guard_ragflow_base_url(self, *, role: str, stage: str, ui_log=None) -> None:
        from tool.maintenance.controllers.release.helper_ops import guard_ragflow_base_url

        return guard_ragflow_base_url(self, role=role, stage=stage, ui_log=ui_log)

    def refresh_release_history(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_release_history as controller_refresh_release_history

        return controller_refresh_release_history(self, *args, **kwargs)

    def _refresh_release_history_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_release_history_impl as controller_refresh_release_history_impl

        return controller_refresh_release_history_impl(self)
    

    def copy_release_history_to_clipboard(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import copy_release_history_to_clipboard as controller_copy_release_history_to_clipboard

        return controller_copy_release_history_to_clipboard(self, *args, **kwargs)

    def _copy_release_history_to_clipboard_impl(self):
        from tool.maintenance.controllers.release_controller import copy_release_history_to_clipboard_impl as controller_copy_release_history_to_clipboard_impl

        return controller_copy_release_history_to_clipboard_impl(self)

    def restart_ragflow_and_ragflowauth(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import restart_ragflow_and_ragflowauth as controller_restart_ragflow_and_ragflowauth

        return controller_restart_ragflow_and_ragflowauth(self, *args, **kwargs)

    def _restart_ragflow_and_ragflowauth_impl(self):
        from tool.maintenance.controllers.release_controller import restart_ragflow_and_ragflowauth_impl as controller_restart_ragflow_and_ragflowauth_impl

        return controller_restart_ragflow_and_ragflowauth_impl(self)

    def stop_ragflow_and_ragflowauth(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import stop_ragflow_and_ragflowauth as controller_stop_ragflow_and_ragflowauth

        return controller_stop_ragflow_and_ragflowauth(self, *args, **kwargs)

    def _stop_ragflow_and_ragflowauth_impl(self):
        from tool.maintenance.controllers.release_controller import stop_ragflow_and_ragflowauth_impl as controller_stop_ragflow_and_ragflowauth_impl

        return controller_stop_ragflow_and_ragflowauth_impl(self)

    def kill_running_backup_job(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import kill_running_backup_job as controller_kill_running_backup_job

        return controller_kill_running_backup_job(self, *args, **kwargs)

    def _kill_running_backup_job_impl(self):
        from tool.maintenance.controllers.release_controller import kill_running_backup_job_impl as controller_kill_running_backup_job_impl

        return controller_kill_running_backup_job_impl(self)

    def refresh_prod_rollback_versions(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_prod_rollback_versions as controller_refresh_prod_rollback_versions

        return controller_refresh_prod_rollback_versions(self, *args, **kwargs)

    def _refresh_prod_rollback_versions_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_prod_rollback_versions_impl as controller_refresh_prod_rollback_versions_impl

        return controller_refresh_prod_rollback_versions_impl(self)

    def rollback_prod_to_selected_version(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import rollback_prod_to_selected_version as controller_rollback_prod_to_selected_version

        return controller_rollback_prod_to_selected_version(self, *args, **kwargs)

    def _rollback_prod_to_selected_version_impl(self):
        from tool.maintenance.controllers.release_controller import rollback_prod_to_selected_version_impl as controller_rollback_prod_to_selected_version_impl

        return controller_rollback_prod_to_selected_version_impl(self)

    def refresh_release_test_versions(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_release_test_versions as controller_refresh_release_test_versions

        return controller_refresh_release_test_versions(self, *args, **kwargs)

    def _refresh_release_test_versions_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_release_test_versions_impl as controller_refresh_release_test_versions_impl

        return controller_refresh_release_test_versions_impl(self)

    def refresh_release_local_backup_list(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import refresh_release_local_backup_list as controller_refresh_release_local_backup_list

        return controller_refresh_release_local_backup_list(self, *args, **kwargs)

    def _refresh_release_local_backup_list_impl(self):
        from tool.maintenance.controllers.release_controller import refresh_release_local_backup_list_impl as controller_refresh_release_local_backup_list_impl

        return controller_refresh_release_local_backup_list_impl(self)
    

    def publish_local_to_test(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import publish_local_to_test as controller_publish_local_to_test

        return controller_publish_local_to_test(self, *args, **kwargs)

    def _publish_local_to_test_impl(self):
        from tool.maintenance.controllers.release_controller import publish_local_to_test_impl as controller_publish_local_to_test_impl

        return controller_publish_local_to_test_impl(self)

    def _sync_local_backup_to_test(self, *, pack_dir: Path | None, ui_log) -> None:
        from tool.maintenance.controllers.release.helper_ops import sync_local_backup_to_test

        return sync_local_backup_to_test(self, pack_dir=pack_dir, ui_log=ui_log)

    def publish_test_to_prod(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import publish_test_to_prod as controller_publish_test_to_prod

        return controller_publish_test_to_prod(self, *args, **kwargs)

    def _publish_test_to_prod_impl(self):
        from tool.maintenance.controllers.release_controller import publish_test_to_prod_impl as controller_publish_test_to_prod_impl

        return controller_publish_test_to_prod_impl(self)

    def publish_test_data_to_prod(self, *args, **kwargs):
        from tool.maintenance.controllers.release_controller import publish_test_data_to_prod as controller_publish_test_data_to_prod

        return controller_publish_test_data_to_prod(self, *args, **kwargs)

    def _publish_test_data_to_prod_impl(self):
        from tool.maintenance.controllers.release_controller import publish_test_data_to_prod_impl as controller_publish_test_data_to_prod_impl

        return controller_publish_test_data_to_prod_impl(self)
