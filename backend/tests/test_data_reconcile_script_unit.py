from __future__ import annotations

import io
import json
import unittest
from unittest import mock

from scripts import data_reconcile


class DataReconcileScriptUnitTests(unittest.TestCase):
    def test_run_mode_uses_report_payload(self):
        service = mock.Mock()
        report = mock.Mock()
        report.to_dict.return_value = {"summary": {"issues": 0}}
        service.report.return_value = report

        payload = data_reconcile.run_mode(service, "report")

        self.assertEqual(payload, {"summary": {"issues": 0}})
        service.report.assert_called_once_with()
        report.to_dict.assert_called_once_with()
        service.apply.assert_not_called()

    def test_run_mode_uses_apply_payload(self):
        service = mock.Mock()
        service.apply.return_value = {"summary": {"db_updates": 1}}

        payload = data_reconcile.run_mode(service, "apply")

        self.assertEqual(payload, {"summary": {"db_updates": 1}})
        service.apply.assert_called_once_with()
        service.report.assert_not_called()

    def test_run_mode_rejects_unknown_mode(self):
        service = mock.Mock()

        with self.assertRaisesRegex(ValueError, "Unsupported reconcile mode"):
            data_reconcile.run_mode(service, "dry-run")

    @mock.patch("scripts.data_reconcile.DataReconcileService")
    def test_main_writes_report_json(self, service_cls):
        service = service_cls.return_value
        report = mock.Mock()
        report.to_dict.return_value = {"summary": {"issues": 2}}
        service.report.return_value = report
        stdout = io.StringIO()

        with mock.patch("sys.stdout", stdout):
            exit_code = data_reconcile.main(["report", "--db", "D:/tmp/auth.db"])

        self.assertEqual(exit_code, 0)
        service_cls.assert_called_once_with(db_path="D:/tmp/auth.db")
        self.assertEqual(json.loads(stdout.getvalue()), {"summary": {"issues": 2}})


if __name__ == "__main__":
    unittest.main()
