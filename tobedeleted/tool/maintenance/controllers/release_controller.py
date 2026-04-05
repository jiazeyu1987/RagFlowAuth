"""Release controller compatibility facade.

Business logic is split across tool.maintenance.controllers.release.* modules.
"""

from .release.version_ops import (
    refresh_release_versions,
    refresh_release_versions_impl,
    refresh_ragflow_base_urls,
    refresh_ragflow_base_urls_impl,
    refresh_release_history,
    refresh_release_history_impl,
    refresh_prod_rollback_versions,
    refresh_prod_rollback_versions_impl,
    rollback_prod_to_selected_version,
    rollback_prod_to_selected_version_impl,
    refresh_release_test_versions,
    refresh_release_test_versions_impl,
    refresh_release_local_backup_list,
    refresh_release_local_backup_list_impl,
)
from .release.publish_ops import (
    publish_local_to_test,
    publish_local_to_test_impl,
    publish_test_to_prod,
    publish_test_to_prod_impl,
    publish_test_data_to_prod,
    publish_test_data_to_prod_impl,
)
from .release.service_ops import (
    copy_release_history_to_clipboard,
    copy_release_history_to_clipboard_impl,
    restart_ragflow_and_ragflowauth,
    restart_ragflow_and_ragflowauth_impl,
    stop_ragflow_and_ragflowauth,
    stop_ragflow_and_ragflowauth_impl,
    kill_running_backup_job,
    kill_running_backup_job_impl,
)
from .release.onlyoffice_ops import (
    deploy_onlyoffice_to_test,
    deploy_onlyoffice_to_test_impl,
    deploy_onlyoffice_to_prod,
    deploy_onlyoffice_to_prod_impl,
)
from .release.smoke_ops import (
    run_smoke_test,
    run_smoke_test_impl,
)

__all__ = [
    "refresh_release_versions",
    "refresh_release_versions_impl",
    "refresh_ragflow_base_urls",
    "refresh_ragflow_base_urls_impl",
    "refresh_release_history",
    "refresh_release_history_impl",
    "copy_release_history_to_clipboard",
    "copy_release_history_to_clipboard_impl",
    "restart_ragflow_and_ragflowauth",
    "restart_ragflow_and_ragflowauth_impl",
    "stop_ragflow_and_ragflowauth",
    "stop_ragflow_and_ragflowauth_impl",
    "kill_running_backup_job",
    "kill_running_backup_job_impl",
    "refresh_prod_rollback_versions",
    "refresh_prod_rollback_versions_impl",
    "rollback_prod_to_selected_version",
    "rollback_prod_to_selected_version_impl",
    "refresh_release_test_versions",
    "refresh_release_test_versions_impl",
    "refresh_release_local_backup_list",
    "refresh_release_local_backup_list_impl",
    "publish_local_to_test",
    "publish_local_to_test_impl",
    "publish_test_to_prod",
    "publish_test_to_prod_impl",
    "publish_test_data_to_prod",
    "publish_test_data_to_prod_impl",
    "deploy_onlyoffice_to_test",
    "deploy_onlyoffice_to_test_impl",
    "deploy_onlyoffice_to_prod",
    "deploy_onlyoffice_to_prod_impl",
    "run_smoke_test",
    "run_smoke_test_impl",
]
