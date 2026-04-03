from __future__ import annotations

from pathlib import Path
import unittest

from backend.services.compliance import validate_gbz01_repo_state
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path) -> None:
    docs = {
        "doc/compliance/maintenance_plan.md": """# 维护计划

版本: v1.0
更新时间: 2026-04-03
当前环境: release 2.0.0
计划覆盖变更类别: os, database, api, config, intended_use
维护责任人: 运维负责人
QA复核人: QA负责人
下次维护计划复核日期: 2026-10-03
仓库外残余项: 线下维护审批单与执行签字记录仍需在线下受控体系归档
""",
        "doc/compliance/maintenance_review_status.md": """# 维护复核状态
版本: v1.0
更新时间: 2026-04-03
最后仓库复核日期: 2026-04-03
下次仓库复核截止日期: 2026-10-03
当前验证状态: validated
预期用途复核状态: current
仓库内证据状态: complete
仓库外证据状态: pending_archive
Residual gap 边界: 线下维护窗口批准、执行签字和培训签到由线下归档
""",
        "doc/compliance/intended_use.md": """# 预期用途
版本: v1.0
更新时间: 2026-04-03

## 维护阶段复核
- os / database / api / config / intended_use 变更前必须执行维护影响判定。
- 预期用途版本变化后，旧验证结论不得继续沿用。
""",
        "doc/compliance/urs.md": "# URS\n\n版本: v1.0\n更新时间: 2026-04-03\n\nURS-013 GBZ-01\n",
        "doc/compliance/srs.md": "# SRS\n\n版本: v1.0\n更新时间: 2026-04-03\n\nSRS-013 URS-013\n",
        "doc/compliance/validation_plan.md": "# VP\n\n版本: v1.0\n更新时间: 2026-04-03\n\nvalidate_gbz01_repo_compliance.py\ntest_gbz01_maintenance_unit\ntest_gbz01_compliance_gate_unit\n",
        "doc/compliance/validation_report.md": "# VR\n\n版本: v1.0\n更新时间: 2026-04-03\n\nGBZ-01\nvalidate_gbz01_repo_compliance.py\nresidual gap\n",
        "doc/compliance/traceability_matrix.md": """# TM

版本: v1.0
更新时间: 2026-04-03

| 需求ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| R4 | URS-004 | SRS-004 | `backend/app/modules/review/routes/workflow.py` | `backend.tests.test_review_workflow_api_unit` | `doc/compliance/approval_workflow_sop.md` | 已验证 |
| R5 | URS-005 | SRS-005 | `backend/services/notification/service.py` | `backend.tests.test_review_notification_integration_unit` | `doc/compliance/approval_notification_sop.md` | 已验证 |
| R7 | URS-007 | SRS-007 | `backend/services/config_change_log_store.py` | `backend.tests.test_r7_compliance_gate_unit` | `doc/compliance/validation_plan.md` | 已验证 |
| R8 | URS-008 | SRS-008 | `backend/app/modules/audit/router.py` | `backend.tests.test_audit_events_api_unit` | `doc/compliance/validation_report.md` | 已验证 |
| R9 | URS-009 | SRS-009 | `backend/database/tenant_paths.py` | `backend.tests.test_tenant_db_isolation_unit` | `doc/compliance/tenant_db_migration_plan.md` | 已验证 |
| R10 | URS-010 | SRS-010 | `backend/services/data_security/store.py` | `backend.tests.test_backup_restore_audit_unit` | `doc/compliance/validation_report.md` | 已验证 |
| FDA-02 | URS-011 | SRS-011 | `backend/app/modules/audit/router.py` | `backend.tests.test_audit_evidence_export_api_unit` | `doc/compliance/validation_report.md` | 已验证 |
| FDA-03 | URS-012 | SRS-012 | `backend/services/compliance/review_package.py` | `backend.tests.test_compliance_review_package_api_unit` | `doc/compliance/review_package_sop.md` | 已验证 |
| GBZ-01 | URS-013 | SRS-013 | `backend/services/compliance/gbz01_maintenance.py`, `backend/services/config_change_log_store.py` | `backend.tests.test_gbz01_maintenance_unit`, `backend.tests.test_gbz01_compliance_gate_unit` | `doc/compliance/intended_use.md`, `doc/compliance/validation_plan.md`, `doc/compliance/validation_report.md` | 已验证 |
""",
    }
    for rel_path, content in docs.items():
        _write(root / rel_path, content)
    for rel_path in (
        "backend/services/compliance/gbz01_maintenance.py",
        "backend/services/compliance/gbz01_validator.py",
        "backend/tests/test_gbz01_maintenance_unit.py",
        "backend/tests/test_gbz01_compliance_gate_unit.py",
        "scripts/validate_gbz01_repo_compliance.py",
    ):
        _write(root / rel_path, "# placeholder\n")


class TestGbz01ComplianceGateUnit(unittest.TestCase):
    def test_repo_gate_passes_with_external_gap_only(self):
        report = validate_gbz01_repo_state(Path(__file__).resolve().parents[2])
        self.assertTrue(report.passed)
        self.assertEqual(report.blocking_issues, [])
        self.assertGreaterEqual(len(report.external_gaps), 1)

    def test_repo_gate_flags_missing_traceability_mapping(self):
        tmp = make_temp_dir(prefix="ragflowauth_gbz01_gate")
        try:
            root = Path(tmp)
            _build_repo(root)
            (root / "doc/compliance/traceability_matrix.md").write_text(
                "# TM\n\n版本: v1.0\n更新时间: 2026-04-03\n",
                encoding="utf-8",
            )
            report = validate_gbz01_repo_state(root)
            self.assertFalse(report.passed)
            self.assertTrue(any(item.code == "required_mapping_missing" for item in report.blocking_issues))
        finally:
            cleanup_dir(tmp)


if __name__ == "__main__":
    unittest.main()
