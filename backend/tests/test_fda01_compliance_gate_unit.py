from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from backend.services.compliance import validate_fda01_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    _write(
        root / "doc/compliance/electronic_signature_policy.md",
        """# Policy
版本: v1.0
更新时间: 2026-04-02
账号唯一性声明: 账号不得共用
仓库外残余项: 线下离岗/转岗签名权限回收记录
当前步骤被授权审批人
""",
    )
    _write(
        root / "doc/compliance/signature_authorization_matrix.md",
        """# Matrix
版本: v1.0
更新时间: 2026-04-02
operation_request_not_current_approver
signature_user_disabled
""",
    )
    _write(root / "doc/compliance/approval_workflow_sop.md", "# SOP\n版本: v1.0\n更新时间: 2026-04-02\n")
    for rel in (
        "backend/app/modules/operation_approvals/router.py",
        "backend/services/operation_approval/service.py",
        "backend/services/operation_approval/handlers.py",
        "backend/services/electronic_signature/service.py",
        "backend/tests/test_operation_approval_service_unit.py",
        "backend/tests/test_electronic_signature_unit.py",
        "backend/tests/test_fda01_compliance_gate_unit.py",
        "scripts/validate_fda01_repo_compliance.py",
    ):
        _write(root / rel, "# placeholder\n")


class TestFda01ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        report = validate_fda01_repo_state(Path(__file__).resolve().parents[2])
        self.assertTrue(report.passed)
        self.assertGreaterEqual(len(report.external_gaps), 1)
        self.assertEqual(report.blocking_issues, [])

    def test_repo_gate_flags_missing_matrix_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_fda01_gate")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/signature_authorization_matrix.md").write_text(
                "# Matrix\n版本: v1.0\n更新时间: 2026-04-02\n",
                encoding="utf-8",
            )
            report = validate_fda01_repo_state(root)
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
