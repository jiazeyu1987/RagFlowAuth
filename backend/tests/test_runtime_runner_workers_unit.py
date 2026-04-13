from __future__ import annotations

import types
import unittest
from unittest.mock import Mock, patch


class RunnerWorkersUnitTests(unittest.TestCase):
    def test_run_server_validates_jwt_secret_before_starting_uvicorn(self):
        from backend.runtime import runner

        fake_uvicorn = types.SimpleNamespace(run=Mock())

        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            with patch.object(runner, "validate_jwt_secret", side_effect=RuntimeError("jwt_secret_key_default_or_empty")):
                with self.assertRaisesRegex(RuntimeError, "jwt_secret_key_default_or_empty"):
                    runner.run_server(workers=1, reload=False)

        fake_uvicorn.run.assert_not_called()

    def test_run_server_uses_import_string_when_workers_gt_one(self):
        from backend.runtime import runner

        fake_uvicorn = types.SimpleNamespace(run=Mock())
        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            with (
                patch.object(runner, "validate_jwt_secret"),
                patch.object(runner.settings, "HOST", "127.0.0.1"),
                patch.object(runner.settings, "PORT", 8001),
            ):
                runner.run_server(host="0.0.0.0", port=9000, workers=2, reload=False)

        fake_uvicorn.run.assert_called_once()
        args, kwargs = fake_uvicorn.run.call_args
        self.assertEqual(args[0], "backend.app.main:app")
        self.assertEqual(kwargs["host"], "0.0.0.0")
        self.assertEqual(kwargs["port"], 9000)
        self.assertEqual(kwargs["workers"], 2)
        self.assertFalse(kwargs["reload"])

    def test_run_server_uses_app_object_when_single_worker(self):
        from backend.runtime import runner

        fake_uvicorn = types.SimpleNamespace(run=Mock())
        fake_app_module = types.SimpleNamespace(app=object())

        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn, "backend.app.main": fake_app_module}):
            with (
                patch.object(runner, "validate_jwt_secret"),
                patch.object(runner.settings, "HOST", "127.0.0.1"),
                patch.object(runner.settings, "PORT", 8001),
            ):
                runner.run_server(workers=1, reload=False)

        fake_uvicorn.run.assert_called_once()
        args, kwargs = fake_uvicorn.run.call_args
        self.assertIs(args[0], fake_app_module.app)
        self.assertEqual(kwargs["workers"], 1)
        self.assertFalse(kwargs["reload"])

    def test_run_server_defaults_to_single_worker_app_object(self):
        from backend.runtime import runner

        fake_uvicorn = types.SimpleNamespace(run=Mock())
        fake_app_module = types.SimpleNamespace(app=object())

        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn, "backend.app.main": fake_app_module}):
            with (
                patch.object(runner, "validate_jwt_secret"),
                patch.object(runner.settings, "HOST", "127.0.0.1"),
                patch.object(runner.settings, "PORT", 8001),
                patch.object(runner.settings, "UVICORN_WORKERS", 1),
            ):
                runner.run_server(workers=None, reload=False)

        fake_uvicorn.run.assert_called_once()
        args, kwargs = fake_uvicorn.run.call_args
        self.assertIs(args[0], fake_app_module.app)
        self.assertEqual(kwargs["workers"], 1)
        self.assertFalse(kwargs["reload"])

    def test_run_server_forces_single_worker_in_reload_mode(self):
        from backend.runtime import runner

        fake_uvicorn = types.SimpleNamespace(run=Mock())
        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            with (
                patch.object(runner, "validate_jwt_secret"),
                patch.object(runner.settings, "HOST", "127.0.0.1"),
                patch.object(runner.settings, "PORT", 8001),
            ):
                runner.run_server(workers=3, reload=True)

        fake_uvicorn.run.assert_called_once()
        args, kwargs = fake_uvicorn.run.call_args
        self.assertEqual(args[0], "backend.app.main:app")
        self.assertEqual(kwargs["workers"], 1)
        self.assertTrue(kwargs["reload"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
