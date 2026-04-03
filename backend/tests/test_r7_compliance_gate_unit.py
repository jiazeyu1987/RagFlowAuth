from __future__ import annotations

import os
from datetime import date
from pathlib import Path
import unittest

from backend.services.compliance import validate_r7_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_minimal_repo(root: Path) -> None:
    _write(
        root / "doc/compliance/gmp_regulatory_baseline.md",
        """# GMP 基线
版本: v1.0
更新时间: 2026-04-02
最新已发布 GMP 基线核对日期: 2026-04-02
下次基线复核截止日期: 2026-10-02

- 最新已发布基线: 国家药监局令第64号
- 发布日期: 2025-11-04
- 生效日期: 2026-11-01
- 当前仓库结论: latest_published_pending_effective
""",
    )
    _write(
        root / "doc/compliance/r7_periodic_review_status.md",
        """# R7 周期复核状态
版本: v1.0
更新时间: 2026-04-02
最后仓库复核日期: 2026-04-02
下次仓库复核截止日期: 2026-10-02
仓库内证据状态: complete
仓库外证据状态: pending_offline_archive
""",
    )
    _write(root / "doc/compliance/intended_use.md", "# Intended Use\n版本: v1.0\n更新时间: 2026-04-02\n")
    _write(root / "doc/compliance/urs.md", "# URS\n版本: v1.0\n更新时间: 2026-04-02\n| URS-007 | R7 | text |\n")
    _write(root / "doc/compliance/srs.md", "# SRS\n版本: v1.0\n更新时间: 2026-04-02\n| SRS-007 | URS-007 | text |\n")
    _write(root / "doc/compliance/risk_assessment.md", "# Risk\n版本: v1.0\n更新时间: 2026-04-02\n| RA-010 | text |\n")
    _write(
        root / "doc/compliance/traceability_matrix.md",
        "# Matrix\n版本: v1.0\n更新时间: 2026-04-02\n| R7 | URS-007 | SRS-007 | `backend/services/compliance/r7_validator.py` | `backend.tests.test_r7_compliance_gate_unit` | doc |\n",
    )
    _write(root / "doc/compliance/validation_plan.md", "# Plan\n版本: v1.0\n更新时间: 2026-04-02\npython scripts/validate_r7_repo_compliance.py\n")
    _write(
        root / "doc/compliance/validation_report.md",
        "# Report\n版本: v1.0\n更新时间: 2026-04-02\n仓库内门禁校验通过；不替代线下签字\n",
    )

    for rel_path in (
        "backend/services/compliance/r7_validator.py",
        "backend/tests/test_r7_compliance_gate_unit.py",
        "backend/tests/test_document_versioning_unit.py",
        "backend/tests/test_config_change_log_unit.py",
        "scripts/validate_r7_repo_compliance.py",
        "fronted/e2e/tests/document.version-history.spec.js",
        "fronted/e2e/tests/admin.config-change-reason.spec.js",
    ):
        _write(root / rel_path, "// placeholder\n")


class TestR7ComplianceGateUnit(unittest.TestCase):
    def test_validator_passes_when_repo_state_complete_and_external_gap_only(self):
        report = validate_r7_repo_state(Path(__file__).resolve().parents[2], as_of=date.fromisoformat("2026-04-02"))
        self.assertTrue(report.passed)
        self.assertGreaterEqual(len(report.external_gaps), 1)
        self.assertEqual(report.blocking_issues, [])

    def test_validator_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_r7_gate_missing")
        try:
            root = Path(tmp)
            _make_minimal_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text(
                "# Matrix\n版本: v1.0\n更新时间: 2026-04-02\n",
                encoding="utf-8",
            )
            report = validate_r7_repo_state(root, as_of=date.fromisoformat("2026-04-02"))
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)

    def test_validator_flags_overdue_periodic_review(self):
        tmp = make_temp_dir(prefix="ragflowauth_r7_gate_due")
        try:
            root = Path(tmp)
            _make_minimal_repo(root)
            (root / "doc/compliance/r7_periodic_review_status.md").write_text(
                """# R7 周期复核状态
版本: v1.0
更新时间: 2026-04-02
最后仓库复核日期: 2026-04-02
下次仓库复核截止日期: 2026-03-31
仓库内证据状态: complete
仓库外证据状态: archived
""",
                encoding="utf-8",
            )
            report = validate_r7_repo_state(root, as_of=date.fromisoformat("2026-04-02"))
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "periodic_review_overdue" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
