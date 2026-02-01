import unittest
from unittest import mock


class TestDataSecurityRunnerStaleLock(unittest.TestCase):
    def test_start_job_if_idle_clears_stale_lock_when_no_active_job(self):
        from backend.app.modules.data_security import runner

        # Reset module-global state for test isolation
        runner._running_job_id = None

        store = mock.Mock()
        store.get_active_job_id.return_value = None
        # First acquire fails (stale), second succeeds after release.
        store.try_acquire_backup_lock.side_effect = [False, True]
        store.release_backup_lock.return_value = None
        store.create_job_v2.return_value = mock.Mock(id=123)

        fake_thread = mock.Mock()
        fake_thread.start.return_value = None

        with mock.patch.object(runner, "DataSecurityStore", return_value=store), mock.patch.object(
            runner, "DataSecurityBackupService"
        ), mock.patch.object(runner.threading, "Thread", return_value=fake_thread):
            job_id = runner.start_job_if_idle(reason="manual", full_backup=False)

        self.assertEqual(job_id, 123)
        store.release_backup_lock.assert_called_once()
        self.assertEqual(store.try_acquire_backup_lock.call_count, 2)
