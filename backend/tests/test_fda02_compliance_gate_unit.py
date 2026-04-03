from __future__ import annotations

from pathlib import Path
import unittest

from backend.services.compliance import validate_fda02_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    _write(
        root / "doc/compliance/inspection_evidence_export_sop.md",
        """# 检查取证导出 SOP
版本: v1.0
更新时间: 2026-04-02
人可读副本: CSV
便携格式: ZIP + JSON
仓库外残余项: 线下交付签收

- 受控导出接口: /api/audit/evidence-export
- 完整性摘要: manifest.json
- 校验清单: checksums.json
""",
    )
    _write(
        root / "doc/compliance/urs.md",
        """# URS
版本: v1.0
更新时间: 2026-04-02
| URS-011 | FDA-02 | 检查取证时必须能够导出人可读副本与便携格式副本。 |
""",
    )
    _write(
        root / "doc/compliance/srs.md",
        """# SRS
版本: v1.0
更新时间: 2026-04-02
| SRS-011 | URS-011 | 通过 /api/audit/evidence-export 输出 ZIP、manifest.json 与 checksums.json。 |
""",
    )
    _write(
        root / "doc/compliance/traceability_matrix.md",
        """# Matrix
版本: v1.0
更新时间: 2026-04-02
| FDA-02 | URS-011 | SRS-011 | `backend/services/audit/evidence_export.py` | `backend.tests.test_audit_evidence_export_api_unit` | `doc/compliance/inspection_evidence_export_sop.md` | 已验证 |
""",
    )
    for rel in (
        "backend/app/modules/audit/router.py",
        "backend/services/audit/evidence_export.py",
        "backend/tests/test_audit_evidence_export_api_unit.py",
        "backend/tests/test_fda02_compliance_gate_unit.py",
        "scripts/validate_fda02_repo_compliance.py",
    ):
        _write(root / rel, "# placeholder\n")


class TestFda02ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        report = validate_fda02_repo_state(Path(__file__).resolve().parents[2])
        self.assertTrue(report.passed)
        self.assertGreaterEqual(len(report.external_gaps), 1)
        self.assertEqual(report.blocking_issues, [])

    def test_repo_gate_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_fda02_gate")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text(
                "# Matrix\n版本: v1.0\n更新时间: 2026-04-02\n",
                encoding="utf-8",
            )
            report = validate_fda02_repo_state(root)
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
