import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4


class TestDataSecurityCancelUnit(unittest.TestCase):
    def test_run_cmd_live_returns_130_on_cancel(self) -> None:
        from backend.services.data_security.common import run_cmd_live

        code, out = run_cmd_live(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            heartbeat_interval_s=0.2,
            cancel_check=lambda: True,
        )
        self.assertEqual(code, 130)
        self.assertIn("[cancelled]", out)

    def test_store_request_cancel_sets_status(self) -> None:
        from backend.database.schema.ensure import ensure_schema
        from backend.services.data_security.store import DataSecurityStore

        # SQLite can return "disk I/O error" on some network-mounted workspaces.
        # Use the OS temp directory for reliability.
        tmp_dir = Path(tempfile.gettempdir())
        db = tmp_dir / f"ragflowauth_auth_cancel_{uuid4().hex}.db"
        try:
            ensure_schema(db)
            store = DataSecurityStore(db_path=db)
            job = store.create_job_v2(kind="full", status="running", message="running")
            job2 = store.request_cancel_job(job.id, reason="unit_test")
            self.assertIn(job2.status, ("canceling", "canceled"))
            self.assertTrue(store.is_cancel_requested(job.id))
        finally:
            try:
                db.unlink(missing_ok=True)  # py3.8+
            except Exception:
                pass
