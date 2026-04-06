from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.services.download_common.manager_mixins import DownloadManagerDelegationMixin


class _FakeExecutionManager:
    def __init__(self, *, stop_requested: bool = False, requested_job=None):
        self._stop_requested = bool(stop_requested)
        self._requested_job = requested_job

    def request_stop(self, *, session_id: str):  # noqa: ARG002
        return self._requested_job

    def is_stop_requested(self, *, session_id: str):  # noqa: ARG002
        return self._stop_requested


class _FakeStore:
    def __init__(self, *, session):
        self._session = session
        self.runtime_updates: list[dict] = []

    def get_session(self, session_id: str):  # noqa: ARG002
        return self._session

    def update_session_runtime(self, **kwargs):
        self.runtime_updates.append(kwargs)
        status = kwargs.get("status")
        if status is not None and self._session is not None:
            self._session.status = status


class _DummyManager(DownloadManagerDelegationMixin):
    def __init__(self, *, store, exec_mgr):
        self.store = store
        self._execution_manager = exec_mgr


class TestDownloadStopCoopUnit(unittest.TestCase):
    def test_is_stop_requested_reads_persisted_session_status(self):
        session = SimpleNamespace(status="stopping", created_by="u1")
        mgr = _DummyManager(store=_FakeStore(session=session), exec_mgr=_FakeExecutionManager(stop_requested=False))
        self.assertTrue(mgr._is_stop_requested("s1"))

    def test_stop_session_download_without_local_thread_marks_stopping(self):
        session = SimpleNamespace(status="running", created_by="u1")
        store = _FakeStore(session=session)
        mgr = _DummyManager(store=store, exec_mgr=_FakeExecutionManager(stop_requested=False, requested_job=None))

        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=True), payload=SimpleNamespace(sub="admin"))
        resp = mgr.stop_session_download(session_id="s1", ctx=ctx)

        self.assertEqual(resp["result"]["status"], "stopping")
        self.assertFalse(resp["result"]["already_finished"])
        self.assertEqual(store.runtime_updates[-1]["status"], "stopping")

    def test_stop_session_download_finished_session_returns_already_finished(self):
        session = SimpleNamespace(status="completed", created_by="u1")
        mgr = _DummyManager(store=_FakeStore(session=session), exec_mgr=_FakeExecutionManager())
        ctx = SimpleNamespace(snapshot=SimpleNamespace(is_admin=True), payload=SimpleNamespace(sub="admin"))

        resp = mgr.stop_session_download(session_id="s1", ctx=ctx)

        self.assertTrue(resp["result"]["already_finished"])
        self.assertEqual(resp["result"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
