import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class TestDataSecurityRouterUnit(unittest.TestCase):
    def test_backup_prerequisites_fail_fast_when_backup_worker_image_missing(self) -> None:
        from backend.app.modules.data_security import router

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

            with patch.object(router, "docker_ok", return_value=(True, "")), patch.object(
                router, "read_compose_project_name", return_value="docker"
            ), patch.object(
                router, "list_docker_volumes_by_prefix", return_value=["docker_esdata01"]
            ), patch.object(
                router, "run_cmd", side_effect=[(0, ""), (1, "missing")]
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    router._assert_backup_prerequisites(deps)

            self.assertEqual(str(ctx.exception), "backup_worker_image_missing:ragflowauth-backend:latest")

    def test_hydrate_job_package_hash_backfills_existing_pack(self) -> None:
        from backend.app.modules.data_security import router
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

            result = router._hydrate_job_package_hash(store, original_job)

            store.update_job.assert_called_once_with(7, package_hash=expected_hash)
            self.assertIs(result, updated_job)


if __name__ == "__main__":
    unittest.main()
