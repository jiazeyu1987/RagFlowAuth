import unittest

from tool.maintenance.core.task_runner import TaskRunner


class TestTaskRunnerUnit(unittest.TestCase):
    def test_runs_and_calls_on_done(self):
        calls = []

        runner = TaskRunner(ui_call=lambda fn: fn())

        runner.run(name="ok", fn=lambda: 123, on_done=lambda res: calls.append((res.ok, res.value)))
        # Thread is daemon; wait briefly for completion.
        import time

        for _ in range(50):
            if calls:
                break
            time.sleep(0.01)

        self.assertEqual(calls, [(True, 123)])

