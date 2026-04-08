import tempfile
import unittest
from pathlib import Path
from uuid import uuid4


class TestDataSecurityStoreLockUnit(unittest.TestCase):
    def _make_store(self, db_path: Path):
        from backend.services.data_security.store import DataSecurityStore

        return DataSecurityStore(db_path=db_path)

    def test_release_backup_lock_requires_matching_owner_or_job(self) -> None:
        from backend.database.schema.ensure import ensure_schema

        tmp_dir = Path(tempfile.gettempdir())
        db_path = tmp_dir / f"ragflowauth_auth_lock_{uuid4().hex}.db"
        try:
            ensure_schema(db_path)
            store_a = self._make_store(db_path)
            store_b = self._make_store(db_path)
            store_c = self._make_store(db_path)

            self.assertTrue(store_a.try_acquire_backup_lock(job_id=42))
            store_b.release_backup_lock()
            self.assertFalse(store_c.try_acquire_backup_lock(job_id=99))

            store_b.release_backup_lock(job_id=42)
            self.assertTrue(store_c.try_acquire_backup_lock(job_id=99))
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except Exception:
                pass

    def test_force_release_backup_lock_only_used_for_stale_recovery(self) -> None:
        from backend.database.schema.ensure import ensure_schema

        tmp_dir = Path(tempfile.gettempdir())
        db_path = tmp_dir / f"ragflowauth_auth_force_lock_{uuid4().hex}.db"
        try:
            ensure_schema(db_path)
            store_a = self._make_store(db_path)
            store_b = self._make_store(db_path)
            store_c = self._make_store(db_path)

            self.assertTrue(store_a.try_acquire_backup_lock(job_id=7))
            store_b.release_backup_lock(force=True)
            self.assertTrue(store_c.try_acquire_backup_lock(job_id=8))
        finally:
            try:
                db_path.unlink(missing_ok=True)
            except Exception:
                pass
