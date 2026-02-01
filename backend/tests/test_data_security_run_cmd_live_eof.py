import unittest
from unittest import mock


class TestRunCmdLiveEOF(unittest.TestCase):
    def test_run_cmd_live_does_not_busy_loop_on_eof(self):
        """
        Regression test: run_cmd_live used to busy-loop at 100% CPU when stdout was at EOF
        and the selector kept reporting it as readable. We simulate a fileobj that returns
        '' forever and ensure the function terminates once the process exits.
        """
        from backend.services.data_security import common

        class _FakeStdout:
            def __init__(self):
                self.closed = False

            def readline(self):
                return ""

            def close(self):
                self.closed = True

        class _FakeProc:
            def __init__(self):
                self.stdout = _FakeStdout()
                self._poll_calls = 0
                self.returncode = 0

            def poll(self):
                # Still running for a couple iterations, then finished.
                self._poll_calls += 1
                return None if self._poll_calls < 3 else 0

            def wait(self, timeout=None):
                return 0

        class _FakeSelector:
            def __init__(self):
                self._registered = set()
                self._select_calls = 0

            def register(self, fileobj, events):
                self._registered.add(fileobj)

            def unregister(self, fileobj):
                self._registered.discard(fileobj)

            def select(self, timeout=None):
                self._select_calls += 1
                # Pretend stdout is always readable until it gets unregistered.
                if self._registered:
                    key = mock.Mock()
                    key.fileobj = next(iter(self._registered))
                    return [(key, None)]
                return []

            def close(self):
                self._registered.clear()

        fake_proc = _FakeProc()
        fake_sel = _FakeSelector()

        with mock.patch("os.name", "posix"), mock.patch.object(common.subprocess, "Popen", return_value=fake_proc), mock.patch(
            "selectors.DefaultSelector", return_value=fake_sel
        ):
            rc, out = common.run_cmd_live(["echo", "x"], heartbeat=None, timeout_s=1)

        self.assertEqual(rc, 0)
        self.assertTrue(fake_proc.stdout.closed)
        # Selector should not be called an extreme number of times in this small scenario.
        self.assertLess(fake_sel._select_calls, 200)
