from __future__ import annotations

import os
from pathlib import Path
import unittest

from backend.database.schema.ensure import ensure_schema
from backend.services.compliance.gbz01_maintenance import ChangeItem, Gbz01MaintenanceService
from backend.services.data_security import DataSecurityStore
from backend.services.upload_settings_store import UploadSettingsStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(root: Path, *, intended_use_version: str = "v1.0") -> None:
    _write(
        root / "docs/compliance/intended_use.md",
        f"""# 预期用途
版本: {intended_use_version}
更新时间: 2026-04-03

## 维护阶段复核
- os / database / api / config / intended_use 变更前必须执行维护影响判定。
- 预期用途版本变化后，旧验证结论不得继续沿用。
""",
    )
    _write(
        root / "docs/compliance/traceability_matrix.md",
        """# 追踪矩阵

版本: v1.0
更新时间: 2026-04-03

| 需求ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| R4 | URS-004 | SRS-004 | `backend/app/modules/review/routes/workflow.py` | `backend.tests.test_review_workflow_api_unit` | `docs/compliance/approval_workflow_sop.md` | 已验证 |
| R5 | URS-005 | SRS-005 | `backend/services/notification/service.py` | `backend.tests.test_review_notification_integration_unit` | `docs/compliance/approval_notification_sop.md` | 已验证 |
| R7 | URS-007 | SRS-007 | `backend/services/compliance/r7_validator.py`, `backend/services/config_change_log_store.py` | `backend.tests.test_r7_compliance_gate_unit` | `docs/compliance/validation_plan.md` | 已验证 |
| R8 | URS-008 | SRS-008 | `backend/services/audit/manager.py`, `backend/app/modules/audit/router.py` | `backend.tests.test_audit_events_api_unit` | `docs/compliance/validation_report.md` | 已验证 |
| R9 | URS-009 | SRS-009 | `backend/database/tenant_paths.py`, `backend/app/core/tenant.py` | `backend.tests.test_tenant_db_isolation_unit` | `docs/compliance/tenant_db_migration_plan.md` | 已验证 |
| R10 | URS-010 | SRS-010 | `backend/services/data_security/restore_service.py`, `backend/services/data_security/store.py` | `backend.tests.test_backup_restore_audit_unit` | `docs/compliance/validation_report.md` | 已验证 |
| FDA-02 | URS-011 | SRS-011 | `backend/app/modules/audit/router.py` | `backend.tests.test_audit_evidence_export_api_unit` | `docs/compliance/validation_report.md` | 已验证 |
| FDA-03 | URS-012 | SRS-012 | `backend/services/compliance/review_package.py` | `backend.tests.test_compliance_review_package_api_unit` | `docs/compliance/review_package_sop.md` | 已验证 |
| GBZ-01 | URS-013 | SRS-013 | `backend/services/compliance/gbz01_maintenance.py`, `backend/services/config_change_log_store.py` | `backend.tests.test_gbz01_maintenance_unit`, `backend.tests.test_gbz01_compliance_gate_unit` | `docs/compliance/intended_use.md`, `docs/compliance/validation_plan.md`, `docs/compliance/validation_report.md` | 已验证 |
""",
    )


class TestGbz01MaintenanceUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_gbz01_maintenance")
        self.repo_root = Path(self._tmp)
        _build_repo(self.repo_root)
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)
        self.service = Gbz01MaintenanceService(repo_root=self.repo_root, db_path=self.db_path)

    def tearDown(self):
        cleanup_dir(self._tmp)

    def test_os_database_api_config_and_intended_use_rules(self):
        cases = [
            ("os", "windows_server_patch", True, False),
            ("database", "sqlite_engine", True, False),
            ("api", "audit_router", True, False),
            ("config", "upload_allowed_extensions", True, False),
            ("config", "data_security_settings", True, False),
            ("intended_use", "intended_use_document", True, True),
        ]
        for category, domain, expected_revalidation, expected_block in cases:
            with self.subTest(category=category, domain=domain):
                assessment = self.service.assess_change_item(
                    ChangeItem(category=category, domain=domain, before={"v": 1}, after={"v": 2}),
                    validated_against_intended_use_version="v1.0",
                )
                self.assertEqual(assessment.requires_revalidation, expected_revalidation)
                self.assertEqual(assessment.blocks_prior_validation, expected_block)
                self.assertTrue(assessment.traceability_refs)
                self.assertTrue(assessment.impacted_artifacts)

    def test_intended_use_version_change_blocks_prior_validation(self):
        root = Path(self._tmp) / "intended_use_changed"
        _build_repo(root, intended_use_version="v1.1")
        service = Gbz01MaintenanceService(repo_root=root)
        assessment = service.assess_change_item(
            ChangeItem(category="intended_use", domain="intended_use_document", before={"v": "v1.0"}, after={"v": "v1.1"}),
            validated_against_intended_use_version="v1.0",
        )
        self.assertTrue(assessment.requires_revalidation)
        self.assertTrue(assessment.blocks_prior_validation)
        self.assertEqual(assessment.validation_status, "blocked")

    def test_validation_completed_closes_maintenance_status(self):
        assessment = self.service.assess_change_item(
            ChangeItem(
                category="config",
                domain="data_security_settings",
                before={"target_local_dir": "/a"},
                after={"target_local_dir": "/b"},
                validation_completed=True,
            ),
            validated_against_intended_use_version="v1.0",
        )
        self.assertTrue(assessment.requires_revalidation)
        self.assertEqual(assessment.validation_status, "closed")
        self.assertIn("docs/compliance/validation_report.md", assessment.impacted_artifacts)

    def test_recent_config_change_logs_use_real_store_records(self):
        UploadSettingsStore(db_path=self.db_path).update_allowed_extensions(
            [".pdf", ".dwg"],
            changed_by="admin-1",
            change_reason="Allow CAD uploads",
        )
        DataSecurityStore(db_path=self.db_path).update_settings(
            {"target_local_dir": "/backup/company_a", "backup_retention_max": 45},
            changed_by="admin-2",
            change_reason="Adjust retention and target path",
        )

        assessments = self.service.assess_recent_config_changes(
            validated_against_intended_use_version="v1.0",
            limit=10,
        )

        by_domain = {item.domain: item for item in assessments}
        self.assertIn("upload_allowed_extensions", by_domain)
        self.assertIn("data_security_settings", by_domain)
        self.assertTrue(by_domain["upload_allowed_extensions"].requires_revalidation)
        self.assertTrue(by_domain["data_security_settings"].requires_revalidation)
        self.assertEqual(by_domain["upload_allowed_extensions"].validation_status, "pending_revalidation")


if __name__ == "__main__":
    unittest.main()
