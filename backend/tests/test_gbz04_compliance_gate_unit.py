from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from backend.services.compliance import validate_gbz04_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/supplier_assessment.md": """# 供应商与第三方组件评估

版本: v1.0
更新时间: 2026-04-03
AVL
OTSS
供应商审核
已知问题
再确认触发
""",
        "doc/compliance/environment_qualification_status.md": """# 环境确认状态

版本: v1.0
更新时间: 2026-04-03
最后仓库复核日期: 2026-04-03
下次仓库复核截止日期: 2026-10-03
仓库内证据状态: complete
仓库外证据状态: pending_archive
Residual gap 边界: 线下签字版供应商审核和 IQ/OQ/PQ 记录仍需归档
IQ
OQ
PQ
""",
        "doc/compliance/controlled_document_register.md": """# 受控文档登记表

版本: v1.0
更新时间: 2026-04-03
当前发布版本: 2.0.0

doc/compliance/supplier_assessment.md
doc/compliance/environment_qualification_status.md
""",
        "doc/compliance/urs.md": "# URS\n\nURS-016 GBZ-04\n",
        "doc/compliance/srs.md": "# SRS\n\nSRS-016 URS-016\n",
        "doc/compliance/traceability_matrix.md": """# TM

| 需求 ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| GBZ-04 | URS-016 | SRS-016 | `backend/services/supplier_qualification.py` | `backend.tests.test_supplier_qualification_api_unit`, `backend.tests.test_gbz04_compliance_gate_unit` | `doc/compliance/supplier_assessment.md` | 已验证（仓库内） |
""",
        "doc/compliance/validation_plan.md": """# VP

validate_gbz04_repo_compliance.py
test_supplier_qualification_api_unit
test_gbz04_compliance_gate_unit
""",
        "doc/compliance/validation_report.md": """# VR

GBZ-04
validate_gbz04_repo_compliance.py
external_supplier_qualification_records_pending
""",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)

    _write(root / "backend/database/schema/supplier_qualification.py", "# schema placeholder\n")
    _write(
        root / "backend/services/supplier_qualification.py",
        "\n".join(
            [
                "supplier_component_requires_requalification",
                "tenant_company_id_required",
                "requalification_required",
                "known_issue_review",
                "migration_plan_summary",
                "QUALIFICATION_PHASE_STATUSES",
                "",
            ]
        ),
    )
    _write(
        root / "backend/app/modules/supplier_qualification/router.py",
        "\n".join(
            [
                "@router.post(\"/supplier-qualifications/components\")",
                "@router.post(\"/supplier-qualifications/components/{component_code}/version-change\")",
                "@router.post(\"/supplier-qualifications/environment-records\")",
                "supplier_component_version_change",
                "environment_qualification_record",
                "",
            ]
        ),
    )
    _write(root / "backend/api/supplier_qualification.py", "# api placeholder\n")
    _write(root / "backend/app/dependencies.py", "supplier_qualification_service\n")
    _write(root / "backend/app/main.py", "supplier_qualification.router,\n")
    _write(root / "backend/services/compliance/gbz04_validator.py", "# validator placeholder\n")
    _write(root / "backend/tests/test_supplier_qualification_api_unit.py", "# placeholder\n")
    _write(root / "backend/tests/test_gbz04_compliance_gate_unit.py", "# placeholder\n")
    _write(root / "scripts/validate_gbz04_repo_compliance.py", "# placeholder\n")


class TestGbz04ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz04_gate_pass")
        try:
            root = Path(tmp)
            _build_repo(root)
            report = validate_gbz04_repo_state(root, as_of=date(2026, 4, 3))
            self.assertTrue(report.passed)
            self.assertEqual(report.blocking_issues, [])
            self.assertEqual(
                [item.code for item in report.external_gaps],
                ["external_supplier_qualification_records_pending"],
            )
        finally:
            cleanup_dir(tmp)

    def test_repo_gate_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz04_gate_fail")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text("# TM\n", encoding="utf-8")
            report = validate_gbz04_repo_state(root, as_of=date(2026, 4, 3))
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
