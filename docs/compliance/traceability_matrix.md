# 追踪矩阵

版本: v1.0
更新时间: 2026-04-14

| 需求 ID | URS | SRS | 实现证据 | 测试证据 | 文档证据 | 状态 |
|---|---|---|---|---|---|---|
| R7 | URS-007 | SRS-007 | `backend/services/compliance/r7_validator.py` | `backend.tests.test_r7_compliance_gate_unit`, `backend.tests.test_document_versioning_unit`, `backend.tests.test_config_change_log_unit`, `fronted/e2e/tests/document.version-history.spec.js`, `fronted/e2e/tests/admin.config-change-reason.spec.js` | `docs/compliance/gmp_regulatory_baseline.md`, `docs/compliance/r7_periodic_review_status.md`, `docs/compliance/risk_assessment.md` | 已建立仓库内门禁 |
| FDA-02 | URS-011 | SRS-011 | `backend/services/audit/evidence_export.py` | `backend.tests.test_audit_evidence_export_api_unit`, `backend.tests.test_fda02_compliance_gate_unit` | `docs/compliance/inspection_evidence_export_sop.md`, `docs/compliance/validation_plan.md`, `docs/compliance/validation_report.md` | 已建立仓库内门禁 |
| FDA-03 | URS-012 | SRS-012 | `backend/services/compliance/review_package.py` | `backend.tests.test_compliance_review_package_api_unit`, `backend.tests.test_fda03_compliance_gate_unit` | `docs/compliance/review_package_sop.md`, `docs/compliance/validation_plan.md`, `docs/compliance/validation_report.md` | 已验证（仓库内） |
| GBZ-01 | URS-013 | SRS-013 | `backend/services/compliance/gbz01_maintenance.py` | `backend.tests.test_gbz01_maintenance_unit`, `backend.tests.test_gbz01_compliance_gate_unit` | `docs/compliance/maintenance_plan.md`, `docs/compliance/maintenance_review_status.md`, `docs/compliance/intended_use.md` | 已建立仓库内门禁 |
| GBZ-02 | URS-014 | SRS-014 | `backend/services/emergency_change.py` | `backend.tests.test_emergency_change_api_unit`, `backend.tests.test_gbz02_compliance_gate_unit` | `docs/compliance/emergency_change_sop.md`, `docs/compliance/emergency_change_status.md`, `docs/compliance/change_control_sop.md` | 已验证（仓库内） |
| GBZ-03 | URS-015 | SRS-015 | `backend/services/compliance/retired_records.py` | `backend.tests.test_retired_document_access_unit`, `backend.tests.test_gbz03_compliance_gate_unit` | `docs/compliance/release_and_retirement_sop.md`, `docs/compliance/retirement_plan.md`, `docs/compliance/retirement_archive_status.md` | 已建立仓库内门禁 |
| GBZ-04 | URS-016 | SRS-016 | `backend/services/supplier_qualification.py` | `backend.tests.test_supplier_qualification_api_unit`, `backend.tests.test_gbz04_compliance_gate_unit` | `docs/compliance/supplier_assessment.md`, `docs/compliance/environment_qualification_status.md` | 已验证（仓库内） |
| GBZ-05 | URS-017 | SRS-017 | `backend/services/training_compliance.py` | `backend.tests.test_training_compliance_api_unit`, `backend.tests.test_gbz05_compliance_gate_unit` | `docs/compliance/training_matrix.md`, `docs/compliance/training_operator_qualification_status.md` | 已验证（仓库内） |
