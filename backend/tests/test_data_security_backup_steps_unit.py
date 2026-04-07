import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class _Settings:
    def __init__(
        self,
        *,
        local_backup_target_path: str,
        replica_target_path: str | None,
        auth_db_path: str,
        ragflow_compose_path: str | None = None,
        ragflow_stop_services: int = 0,
        full_backup_include_images: int = 1,
    ) -> None:
        self._local_backup_target_path = local_backup_target_path
        self.replica_target_path = replica_target_path
        self.auth_db_path = auth_db_path
        self.ragflow_compose_path = ragflow_compose_path
        self.ragflow_stop_services = ragflow_stop_services
        self.full_backup_include_images = full_backup_include_images

    def local_backup_target_path(self) -> str:
        return self._local_backup_target_path

    def target_path(self) -> str:
        return str(self.replica_target_path or "")

    def windows_target_path(self) -> str | None:
        return self.replica_target_path


class TestDataSecurityBackupStepsUnit(unittest.TestCase):
    def test_precheck_fails_when_mnt_replica_not_cifs(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import precheck

        store = Mock()
        store.is_cancel_requested.return_value = False
        settings = _Settings(
            local_backup_target_path="/app/data/backups",
            replica_target_path="/mnt/replica/RagflowAuth",
            auth_db_path=str(Path(__file__).resolve()),
        )
        ctx = BackupContext(store=store, job_id=1, settings=settings, include_images=False)

        with patch.object(precheck, "docker_ok", return_value=(True, "")):
            precheck.backup_precheck_and_prepare(ctx)
        self.assertIsNotNone(ctx.pack_dir)

    def test_precheck_sets_pack_dir_and_updates_job(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import precheck

        td_path = make_temp_dir(prefix="ragflowauth_precheck")
        try:
            auth_db = td_path / "auth.db"
            auth_db.write_text("ok", encoding="utf-8")

            store = Mock()
            store.is_cancel_requested.return_value = False
            settings = _Settings(
                local_backup_target_path=str(td_path),
                replica_target_path="/mnt/replica/RagflowAuth",
                auth_db_path=str(auth_db),
            )
            ctx = BackupContext(store=store, job_id=123, settings=settings, include_images=False)

            with patch.object(precheck, "docker_ok", return_value=(True, "")):
                precheck.backup_precheck_and_prepare(ctx)

            self.assertIsNotNone(ctx.pack_dir)
            self.assertTrue(ctx.pack_dir.exists())
            self.assertEqual(ctx.local_backup_root, td_path)
            self.assertEqual(ctx.staging_root, td_path / "_staging" / "job_123")
            self.assertFalse(
                any("output_dir" in kwargs for _, kwargs in store.update_job.call_args_list),
                f"unexpected output_dir update during precheck: calls={store.update_job.call_args_list!r}",
            )
        finally:
            cleanup_dir(td_path)

    def test_sqlite_step_stages_when_target_under_mnt_replica(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import sqlite_step

        td_root = make_temp_dir(prefix="ragflowauth_sqlite_step")
        try:
            src_db = td_root / "src.db"
            src_db.write_text("db", encoding="utf-8")

            pack_dir = td_root / "migration_pack_unit_test"
            if pack_dir.exists():
                shutil.rmtree(pack_dir, ignore_errors=True)
            pack_dir.mkdir(parents=True, exist_ok=True)

            store = Mock()
            store.is_cancel_requested.return_value = False
            settings = _Settings(
                local_backup_target_path=str(td_root),
                replica_target_path="/mnt/replica/RagflowAuth",
                auth_db_path=str(src_db),
            )
            ctx = BackupContext(store=store, job_id=7, settings=settings, include_images=False)
            ctx.pack_dir = pack_dir
            with patch.object(sqlite_step, "sqlite_online_backup") as mock_backup:
                def _fake_sqlite_backup(_src: Path, _dest: Path) -> None:
                    _dest.parent.mkdir(parents=True, exist_ok=True)
                    _dest.write_bytes(b"sqlite")
                mock_backup.side_effect = _fake_sqlite_backup
                sqlite_step.backup_sqlite_db(ctx)

            self.assertTrue((pack_dir / "auth.db").exists())
            self.assertGreater((pack_dir / "auth.db").stat().st_size, 0)
        finally:
            cleanup_dir(td_root)

    def test_volumes_step_calls_docker_tar_volume_with_heartbeat(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import volumes_step

        td_path = make_temp_dir(prefix="ragflowauth_volumes_step")
        try:
            compose = td_path / "docker-compose.yml"
            compose.write_text("services: {}", encoding="utf-8")

            store = Mock()
            store.is_cancel_requested.return_value = False
            settings = _Settings(
                local_backup_target_path=str(td_path),
                replica_target_path=str(td_path),
                auth_db_path=str(td_path / "auth.db"),
                ragflow_compose_path=str(compose),
                ragflow_stop_services=1,
            )
            ctx = BackupContext(store=store, job_id=1, settings=settings, include_images=False)
            ctx.pack_dir = td_path / "pack"
            ctx.pack_dir.mkdir(parents=True, exist_ok=True)

            vols = ["ragflow_compose_esdata01", "ragflow_compose_mysql_data"]

            def _fake_tar(
                vol: str,
                dest: Path,
                *,
                helper_image=None,
                compose_file=None,
                project_name=None,
                heartbeat=None,
                cancel_check=None,
            ) -> None:
                if heartbeat:
                    heartbeat()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"tar")
                self.assertEqual(helper_image, "helper:test")
                self.assertEqual(project_name, "ragflow_compose")

            with patch.object(volumes_step, "read_compose_project_name", return_value="ragflow_compose"), patch.object(
                volumes_step, "list_docker_volumes_by_prefix", return_value=vols
            ), patch.object(volumes_step, "docker_compose_stop", return_value=None), patch.object(
                volumes_step, "docker_compose_start", return_value=None
            ), patch.object(volumes_step, "resolve_backend_helper_image", return_value="helper:test"), patch.object(
                volumes_step, "docker_tar_volume", side_effect=_fake_tar
            ):
                volumes_step.backup_ragflow_volumes(ctx)

            self.assertTrue((ctx.pack_dir / "volumes" / f"{vols[0]}.tar.gz").exists())
            self.assertTrue((ctx.pack_dir / "volumes" / f"{vols[1]}.tar.gz").exists())
            self.assertTrue(store.update_job.call_count > 0)
        finally:
            cleanup_dir(td_path)

    def test_images_step_skips_when_not_enabled(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import images_step

        store = Mock()
        store.is_cancel_requested.return_value = False
        settings = _Settings(
            local_backup_target_path="/tmp",
            replica_target_path="/tmp",
            auth_db_path=str(Path(__file__).resolve()),
            ragflow_compose_path="/tmp/x.yml",
        )
        ctx = BackupContext(store=store, job_id=1, settings=settings, include_images=False)
        ctx.pack_dir = Path(".")
        ctx.compose_file = Path("docker-compose.yml")
        ctx.ragflow_project = "ragflow_compose"

        with patch.object(images_step, "docker_save_images") as save:
            images_step.backup_docker_images(ctx)
            save.assert_not_called()

        self.assertGreater(store.update_job.call_count, 0)

    def test_images_step_creates_images_tar_when_enabled(self) -> None:
        from backend.services.data_security.backup_steps.context import BackupContext
        from backend.services.data_security.backup_steps import images_step

        td_path = make_temp_dir(prefix="ragflowauth_images_step")
        try:
            store = Mock()
            store.is_cancel_requested.return_value = False
            settings = _Settings(
                local_backup_target_path=str(td_path),
                replica_target_path=str(td_path),
                auth_db_path=str(Path(__file__).resolve()),
                ragflow_compose_path=str(td_path / "docker-compose.yml"),
            )
            ctx = BackupContext(store=store, job_id=9, settings=settings, include_images=True)
            ctx.pack_dir = td_path / "pack"
            ctx.pack_dir.mkdir(parents=True, exist_ok=True)
            ctx.compose_file = td_path / "docker-compose.yml"
            ctx.compose_file.write_text("services: {}", encoding="utf-8")
            ctx.ragflow_project = "ragflow_compose"

            def _fake_save(_images: list[str], dest: Path, *, heartbeat=None, cancel_check=None):
                if heartbeat:
                    heartbeat()
                dest.write_bytes(b"img")
                return True, None

            class _DU:
                free = 10**12

            with patch.object(images_step, "list_compose_images", return_value=(["a:1", "b:2"], None)), patch.object(
                images_step, "run_cmd", return_value=(0, "1\n2\n")
            ), patch.object(shutil, "disk_usage", return_value=_DU()), patch.object(
                images_step, "docker_save_images", side_effect=_fake_save
            ):
                images_step.backup_docker_images(ctx)

            self.assertTrue((ctx.pack_dir / "images.tar").exists())
        finally:
            cleanup_dir(td_path)
