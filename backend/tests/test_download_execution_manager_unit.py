import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertIs(mgr_a.get_job(session_id="s1"), worker)
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
        self.assertIsNone(mgr_a.get_job(session_id="s1"))
        self.assertFalse(mgr_a.is_stop_requested(session_id="s1"))
        self.assertFalse(mgr_a.is_cancelled(session_id="s1"))

    def test_download_root_and_session_dir(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_dirs")
        temp_dir = tempfile.mkdtemp(prefix="download-exec-")
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        root = mgr.download_root(setting_value=temp_dir, setting_name="UNIT_DOWNLOAD_DIR")
        session_dir = mgr.session_dir(root=root, actor_id="user-1", session_id="sess-1")

        self.assertEqual(root, Path(temp_dir))
        self.assertTrue(root.exists())
        self.assertTrue(session_dir.exists())
        self.assertEqual(session_dir, Path(temp_dir) / "user-1" / "sess-1")

    def test_download_root_rejects_missing_setting_value(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_missing_dir")

        with self.assertRaisesRegex(ValueError, "UNIT_DOWNLOAD_DIR_required"):
            mgr.download_root(setting_value="   ", setting_name="UNIT_DOWNLOAD_DIR")

    def test_start_job_prevents_duplicate_active_session(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_duplicate")
        stop_event_1 = threading.Event()
        stop_event_2 = threading.Event()
        started_tags: list[str] = []

        def _target(tag: str, stop_event: threading.Event):
            started_tags.append(tag)
            stop_event.wait(1.0)

        worker1 = mgr.start_job(
            session_id="dup-s1",
            target=_target,
            kwargs={"tag": "first", "stop_event": stop_event_1},
            name_prefix="unit-job",
        )
        worker2 = mgr.start_job(
            session_id="dup-s1",
            target=_target,
            kwargs={"tag": "second", "stop_event": stop_event_2},
            name_prefix="unit-job",
        )

        self.assertIs(worker1, worker2)
        self.assertEqual(started_tags, ["first"])

        stop_event_1.set()
        worker1.join(timeout=1.0)

        worker3 = mgr.start_job(
            session_id="dup-s1",
            target=_target,
            kwargs={"tag": "third", "stop_event": stop_event_2},
            name_prefix="unit-job",
        )
        self.assertIsNot(worker1, worker3)
        self.assertEqual(started_tags, ["first", "third"])

        stop_event_2.set()
        worker3.join(timeout=1.0)
        self.assertIsNone(mgr.get_job(session_id="dup-s1"))

    def test_start_job_rolls_back_registry_when_thread_start_fails(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_start_fail")

        def _target():
            time.sleep(0.01)

        with patch.object(threading.Thread, "start", side_effect=RuntimeError("start_failed")):
            with self.assertRaises(RuntimeError):
                mgr.start_job(
                    session_id="s-fail",
                    target=_target,
                    kwargs={},
                    name_prefix="unit-job",
                )

        self.assertIsNone(mgr.get_job(session_id="s-fail"))
        self.assertFalse(mgr.is_cancelled(session_id="s-fail"))
        self.assertFalse(mgr.is_stop_requested(session_id="s-fail"))

    def test_start_job_is_atomic_under_concurrent_calls(self):
        mgr = DownloadExecutionManager(namespace="unit_exec_atomic")
        stop_event = threading.Event()
        barrier = threading.Barrier(6)
        results = []
        results_lock = threading.Lock()

        def _target():
            stop_event.wait(1.0)

        def _starter():
            barrier.wait(timeout=1.0)
            worker = mgr.start_job(
                session_id="atomic-s1",
                target=_target,
                kwargs={},
                name_prefix="unit-job",
            )
            with results_lock:
                results.append(worker)

        starters = [threading.Thread(target=_starter, daemon=True) for _ in range(6)]
        for t in starters:
            t.start()
        for t in starters:
            t.join(timeout=1.0)

        self.assertEqual(len(results), 6)
        unique_workers = {id(worker) for worker in results}
        self.assertEqual(len(unique_workers), 1)
        self.assertIs(mgr.get_job(session_id="atomic-s1"), results[0])

        stop_event.set()
        results[0].join(timeout=1.0)
        self.assertIsNone(mgr.get_job(session_id="atomic-s1"))


if __name__ == "__main__":
    unittest.main()
