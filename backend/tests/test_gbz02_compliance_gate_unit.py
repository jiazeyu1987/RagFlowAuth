from __future__ import annotations

from pathlib import Path
import unittest

from backend.services.compliance import validate_gbz02_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/emergency_change_sop.md": """# 紧急变更 SOP

版本: v1.0
更新时间: 2026-04-03

先授权后部署再复盘
authorization_basis
risk_control
post_review_summary
capa_actions
""",
        "doc/compliance/emergency_change_status.md": """# 紧急变更状态

版本: v1.0
更新时间: 2026-04-03
最后仓库复核日期: 2026-04-03
下次仓库复核截止日期: 2026-10-03
仓库内证据状态: complete
仓库外证据状态: pending_archive
Residual gap 边界: 线下紧急变更执行单、签字版授权和产品评审记录仍需在线下归档
""",
        "doc/compliance/change_control_sop.md": """# 变更控制 SOP

紧急变更
先授权
后部署
事后评审
""",
        "doc/compliance/urs.md": "# URS\n\n| URS ID | 对应需求 | 用户需求 |\n|---|---|---|\n| URS-014 | GBZ-02 | 紧急变更必须先授权后部署再补齐评审。 |\n",
        "doc/compliance/srs.md": "# SRS\n\n| SRS ID | 对应 URS | 软件要求 | 主要实现证据 |\n|---|---|---|---|\n| SRS-014 | URS-014 | 紧急变更流程落库。 | `backend/services/emergency_change.py` |\n",
        "doc/compliance/traceability_matrix.md": """# TM

| 需求 ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| GBZ-02 | URS-014 | SRS-014 | `backend/services/emergency_change.py` | `backend.tests.test_emergency_change_api_unit`, `backend.tests.test_gbz02_compliance_gate_unit` | `doc/compliance/emergency_change_sop.md` | 已验证（仓库内） |
""",
        "doc/compliance/validation_plan.md": """# VP

validate_gbz02_repo_compliance.py
test_emergency_change_api_unit
test_gbz02_compliance_gate_unit
""",
        "doc/compliance/validation_report.md": """# VR

GBZ-02
validate_gbz02_repo_compliance.py
external_emergency_change_execution_pending
""",
        "doc/compliance/controlled_document_register.md": """# 受控文档登记表

doc/compliance/emergency_change_sop.md
doc/compliance/emergency_change_status.md
""",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)
    for rel_path in (
        "backend/database/schema/emergency_changes.py",
        "backend/services/emergency_change.py",
        "backend/app/modules/emergency_changes/router.py",
        "backend/api/emergency_changes.py",
        "backend/services/compliance/gbz02_validator.py",
        "backend/tests/test_emergency_change_api_unit.py",
        "backend/tests/test_gbz02_compliance_gate_unit.py",
        "scripts/validate_gbz02_repo_compliance.py",
    ):
        _write(root / rel_path, "# placeholder\n")


class TestGbz02ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        report = validate_gbz02_repo_state(Path(__file__).resolve().parents[2])
        self.assertTrue(report.passed)
        self.assertEqual(report.blocking_issues, [])
        self.assertGreaterEqual(len(report.external_gaps), 1)

    def test_repo_gate_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz02_gate")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text("# TM\n", encoding="utf-8")
            report = validate_gbz02_repo_state(root)
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
