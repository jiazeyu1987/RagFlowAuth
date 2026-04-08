import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class TestDataSecurityRouterUnit(unittest.TestCase):
    def test_settings_response_uses_local_backup_fields_without_windows_stats(self) -> None:
        from backend.app.modules.data_security import support

        settings = SimpleNamespace(
            enabled=True,
            interval_minutes=60,
            target_mode="local",
            target_ip="",
            target_share_name="",
            target_subdir="",
            target_local_dir="/backup/local",
            ragflow_compose_path="docker-compose.yml",
            ragflow_project_name="ragflow",
            ragflow_stop_services=False,
            auth_db_path="data/auth.db",
            updated_at_ms=123,
            last_run_at_ms=456,
            full_backup_enabled=True,
            full_backup_include_images=False,
            backup_retention_max=9,
            incremental_schedule="0 * * * *",
            full_backup_schedule="0 1 * * *",
            last_incremental_backup_time_ms=None,
            last_full_backup_time_ms=None,
            replica_enabled=True,
            replica_target_path="/mnt/replica/RagflowAuth",
            replica_subdir_format="date",
        )

        with patch.object(
            support,
            "_backup_pack_stats",
            return_value={
                "local_backup_target_path": "/backup/local",
                "local_backup_pack_count": 2,
                "local_backup_pack_count_skipped": False,
                "windows_backup_target_path": "",
                "windows_backup_pack_count": 0,
                "windows_backup_pack_count_skipped": False,
            },
        ):
            payload = support._settings_response(settings)

        self.assertTrue(payload["full_backup_enabled"])
        self.assertFalse(payload["full_backup_include_images"])
        self.assertEqual(payload["replica_target_path"], "/mnt/replica/RagflowAuth")
        self.assertEqual(payload["replica_subdir_format"], "date")
        self.assertEqual(payload["backup_retention_max"], 9)
        self.assertEqual(payload["local_backup_target_path"], "/backup/local")
        self.assertEqual(payload["windows_backup_target_path"], "")

    def test_backup_prerequisites_fail_fast_when_backup_worker_image_missing(self) -> None:
        from backend.app.modules.data_security import support

        with tempfile.TemporaryDirectory(prefix="ragflowauth_ds_router_") as temp_dir:
            root = Path(temp_dir)
            compose = root / "docker-compose.yml"
            compose.write_text("services: {}", encoding="utf-8")
            auth_db = root / "auth.db"
            auth_db.write_text("ok", encoding="utf-8")

            settings = SimpleNamespace(
                local_backup_target_path=lambda: str(root / "backups"),
                auth_db_path=str(auth_db),
                ragflow_compose_path=str(compose),
            )
            deps = SimpleNamespace(
                data_security_store=SimpleNamespace(get_settings=lambda: settings),
            )

            with patch.object(support, "docker_ok", return_value=(True, "")), patch.object(
                support, "read_compose_project_name", return_value="docker"
            ), patch.object(
                support, "list_docker_volumes_by_prefix", return_value=["docker_esdata01"]
            ), patch.object(
                support, "resolve_backend_helper_image", side_effect=RuntimeError(
                    "backup_worker_image_not_found:container=ragflowauth-backend"
                )
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    support._assert_backup_prerequisites(deps)

            self.assertEqual(str(ctx.exception), "backup_worker_image_not_found:container=ragflowauth-backend")

    def test_hydrate_job_package_hash_backfills_existing_pack(self) -> None:
        from backend.app.modules.data_security import support
        from backend.services.data_security.backup_service import _compute_backup_package_hash

        with tempfile.TemporaryDirectory(prefix="ragflowauth_ds_pack_") as temp_dir:
            pack_dir = Path(temp_dir) / "migration_pack_20260405_000000"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "auth.db").write_text("sqlite", encoding="utf-8")
            (pack_dir / "manifest.json").write_text("{}", encoding="utf-8")
            expected_hash = _compute_backup_package_hash(pack_dir)

            original_job = SimpleNamespace(
                id=7,
                package_hash=None,
                output_dir=str(pack_dir),
            )
            updated_job = SimpleNamespace(
                id=7,
                package_hash=expected_hash,
                output_dir=str(pack_dir),
            )
            store = Mock()
            store.update_job.return_value = updated_job

            result = support._hydrate_job_package_hash(store, original_job)

            store.update_job.assert_called_once_with(7, package_hash=expected_hash)
            self.assertIs(result, updated_job)


if __name__ == "__main__":
    unittest.main()
