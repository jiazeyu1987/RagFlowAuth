import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path

from backend.services.download_execution import DownloadExecutionManager


class TestDownloadExecutionManagerUnit(unittest.TestCase):
    def test_normalize_and_build_stats(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_a")

        cfg = mgr.normalize_source_configs(
            source_configs={
                "google_patents": {"enabled": True, "limit": 5000},
                "uspto": {"enabled": False, "limit": 0},
            },
            source_keys=("uspto", "google_patents"),
            default_limit=10,
            max_limit=1000,
        )

        self.assertEqual(
            cfg,
            {
                "uspto": {"enabled": False, "limit": 10},
                "google_patents": {"enabled": True, "limit": 1000},
            },
        )

        stats = mgr.build_source_stats(
            enabled_sources=["google_patents"],
            source_cfg=cfg,
            default_limit=10,
        )
        self.assertEqual(stats["google_patents"]["requested_limit"], 1000)
        self.assertEqual(stats["google_patents"]["failed_reasons"], {})

    def test_job_registry_and_namespace_isolation(self):
        mgr_a = DownloadExecutionManager(namespace="unit_exec_ns_a")
        mgr_b = DownloadExecutionManager(namespace="unit_exec_ns_b")
        stop_event = threading.Event()

        def _target():
            stop_event.wait(1.0)

        worker = mgr_a.start_job(
            session_id="s1",
            target=_target,
            kwargs={},
            name_prefix="unit-job",
        )
        self.assertTrue(worker.is_alive())
        self.assertFalse(mgr_a.is_stop_requested(session_id="s1"))
        self.assertFalse(mgr_b.is_stop_requested(session_id="s1"))

        returned = mgr_a.request_stop(session_id="s1")
        self.assertIs(returned, worker)
        self.assertTrue(mgr_a.is_stop_requested(session_id="s1"))
        self.assertFalse(mgr_b.is_stop_requested(session_id="s1"))

        mgr_a.cancel_job(session_id="s1")
        self.assertTrue(mgr_a.is_cancelled(session_id="s1"))
        self.assertFalse(mgr_b.is_cancelled(session_id="s1"))

        stop_event.set()
        worker.join(timeout=1.0)
        mgr_a.finish_job(session_id="s1")
        self.assertFalse(mgr_a.is_stop_requested(session_id="s1"))
        self.assertFalse(mgr_a.is_cancelled(session_id="s1"))

    def test_download_root_and_session_dir(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_dirs")
        temp_dir = tempfile.mkdtemp(prefix="download-exec-")
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        root = mgr.download_root(setting_value=temp_dir, fallback_dir="unused")
        session_dir = mgr.session_dir(root=root, actor_id="user-1", session_id="sess-1")

        self.assertEqual(root, Path(temp_dir))
        self.assertTrue(root.exists())
        self.assertTrue(session_dir.exists())
        self.assertEqual(session_dir, Path(temp_dir) / "user-1" / "sess-1")


if __name__ == "__main__":
    unittest.main()
