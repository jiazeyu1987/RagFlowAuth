from __future__ import annotations

from tool.maintenance.features.docker_cleanup_images import cleanup_docker_images as feature_cleanup_docker_images
from tool.maintenance.features.kill_backup_job import (
    kill_running_backup_job as feature_kill_running_backup_job,
)
from tool.maintenance.features.local_backup_catalog import list_local_backups as feature_list_local_backups
from tool.maintenance.features.onlyoffice_deploy import (
    deploy_onlyoffice_from_local as feature_deploy_onlyoffice_from_local,
)
from tool.maintenance.features.release_history import load_release_history as feature_load_release_history
from tool.maintenance.features.release_publish import (
    get_server_version_info as feature_get_server_version_info,
    publish_from_test_to_prod as feature_publish_from_test_to_prod,
)
from tool.maintenance.features.release_publish_data_test_to_prod import (
    publish_data_from_test_to_prod as feature_publish_data_from_test_to_prod,
)
from tool.maintenance.features.release_publish_local_to_test import (
    publish_from_local_to_test as feature_publish_from_local_to_test,
)
from tool.maintenance.features.release_rollback import (
    feature_list_ragflowauth_versions as feature_list_ragflowauth_versions,
    feature_rollback_ragflowauth_to_version as feature_rollback_ragflowauth_to_version,
)
from tool.maintenance.features.replica_backups import (
    delete_replica_backup_dir as feature_delete_replica_backup_dir,
    list_replica_backup_dirs as feature_list_replica_backup_dirs,
)
from tool.maintenance.features.restart_services import (
    restart_ragflow_and_ragflowauth as feature_restart_ragflow_and_ragflowauth,
)
from tool.maintenance.features.smoke_test import feature_run_smoke_test
from tool.maintenance.features.stop_services import stop_ragflow_and_ragflowauth as feature_stop_ragflow_and_ragflowauth
from tool.maintenance.features.windows_share_mount import mount_windows_share as feature_mount_windows_share
from tool.maintenance.features.windows_share_status import check_mount_status as feature_check_mount_status
from tool.maintenance.features.windows_share_unmount import unmount_windows_share as feature_unmount_windows_share

__all__ = [
    "feature_cleanup_docker_images",
    "feature_mount_windows_share",
    "feature_unmount_windows_share",
    "feature_check_mount_status",
    "feature_list_local_backups",
    "feature_delete_replica_backup_dir",
    "feature_list_replica_backup_dirs",
    "feature_get_server_version_info",
    "feature_publish_from_test_to_prod",
    "feature_publish_from_local_to_test",
    "feature_publish_data_from_test_to_prod",
    "feature_run_smoke_test",
    "feature_list_ragflowauth_versions",
    "feature_rollback_ragflowauth_to_version",
    "feature_load_release_history",
    "feature_restart_ragflow_and_ragflowauth",
    "feature_stop_ragflow_and_ragflowauth",
    "feature_kill_running_backup_job",
    "feature_deploy_onlyoffice_from_local",
]

