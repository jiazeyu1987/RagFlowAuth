from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from backend.services.compliance import validate_gbz05_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/training_matrix.md": """# 培训矩阵

版本: v1.1
更新时间: 2026-04-03
TR-001
TR-002
document_review
restore_drill_execute
curriculum_version
""",
        "doc/compliance/training_operator_qualification_status.md": """# 培训与操作员认证状态

版本: v1.0
更新时间: 2026-04-03
最后仓库复核日期: 2026-04-03
下次仓库复核截止日期: 2026-10-03
仓库内证据状态: complete
仓库外证据状态: pending_archive
Residual gap 边界: 线下培训签到、考核签字和例外放行记录仍需归档
""",
        "doc/compliance/controlled_document_register.md": """# 受控文档登记表

版本: v1.3
更新时间: 2026-04-03
当前发布版本: 2.0.0

doc/compliance/training_matrix.md
doc/compliance/training_operator_qualification_status.md
""",
        "doc/compliance/urs.md": "# URS\n\nURS-017 GBZ-05\n",
        "doc/compliance/srs.md": "# SRS\n\nSRS-017 URS-017\n",
        "doc/compliance/traceability_matrix.md": """# TM

| 需求 ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| GBZ-05 | URS-017 | SRS-017 | `backend/services/training_compliance.py` | `backend.tests.test_training_compliance_api_unit`, `backend.tests.test_gbz05_compliance_gate_unit` | `doc/compliance/training_matrix.md` | 已验证（仓库内） |
""",
        "doc/compliance/validation_plan.md": """# VP

validate_gbz05_repo_compliance.py
test_training_compliance_api_unit
test_gbz05_compliance_gate_unit
""",
        "doc/compliance/validation_report.md": """# VR

GBZ-05
validate_gbz05_repo_compliance.py
external_training_qualification_records_pending
""",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)

    _write(root / "backend/database/schema/training_compliance.py", "# schema placeholder\n")
    _write(
        root / "backend/services/training_compliance.py",
        "\n".join(
            [
                "training_curriculum_outdated",
                "operator_certification_expired",
                "document_review",
                "restore_drill_execute",
                "effectiveness_status",
                "training_requirement_not_configured",
                "",
            ]
        ),
    )
    _write(root / "backend/app/core/training_support.py", "assert_user_training_for_action\n")
    _write(
        root / "backend/app/modules/training_compliance/router.py",
        "\n".join(
            [
                "@router.post(\"/training-compliance/requirements\")",
                "@router.post(\"/training-compliance/records\")",
                "@router.post(\"/training-compliance/certifications\")",
                "@router.get(\"/training-compliance/actions/{controlled_action}/users/{user_id}\")",
                "training_record_create",
                "operator_certification_create",
                "",
            ]
        ),
    )
    _write(root / "backend/api/training_compliance.py", "# api placeholder\n")
    _write(root / "backend/app/dependencies.py", "training_compliance_service\n")
    _write(root / "backend/app/main.py", "training_compliance.router,\n")
    _write(root / "backend/app/modules/operation_approvals/router.py", "assert_user_training_for_action\n")
    _write(root / "backend/services/operation_approval/service.py", "# placeholder\n")
    _write(root / "backend/app/modules/data_security/router.py", "assert_user_training_for_action\n")
    _write(root / "backend/services/compliance/gbz05_validator.py", "# validator placeholder\n")
    _write(root / "backend/tests/test_training_compliance_api_unit.py", "# placeholder\n")
    _write(root / "backend/tests/test_gbz05_compliance_gate_unit.py", "# placeholder\n")
    _write(root / "scripts/validate_gbz05_repo_compliance.py", "# placeholder\n")


class TestGbz05ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz05_gate_pass")
        try:
            root = Path(tmp)
            _build_repo(root)
            report = validate_gbz05_repo_state(root, as_of=date(2026, 4, 3))
            self.assertTrue(report.passed)
            self.assertEqual(report.blocking_issues, [])
            self.assertEqual(
                [item.code for item in report.external_gaps],
                ["external_training_qualification_records_pending"],
            )
        finally:
            cleanup_dir(tmp)

    def test_repo_gate_flags_missing_runtime_gate(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz05_gate_fail")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "backend/app/modules/operation_approvals/router.py").write_text("# missing gate\n", encoding="utf-8")
            report = validate_gbz05_repo_state(root, as_of=date(2026, 4, 3))
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "runtime_training_gate_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
