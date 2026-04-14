# 验证计划

版本: v1.0
更新时间: 2026-04-14

## 1. 仓库内门禁命令

- `python scripts/validate_fda01_repo_compliance.py`
- `python scripts/validate_fda02_repo_compliance.py`
- `python scripts/validate_fda03_repo_compliance.py`
- `python scripts/validate_gbz01_repo_compliance.py`
- `python scripts/validate_gbz02_repo_compliance.py`
- `python scripts/validate_gbz03_repo_compliance.py`
- `python scripts/validate_gbz04_repo_compliance.py`
- `python scripts/validate_gbz05_repo_compliance.py`
- `python scripts/validate_r7_repo_compliance.py`

## 2. 关键自动化测试

- `backend.tests.test_operation_approval_service_unit`
- `backend.tests.test_electronic_signature_unit`
- `backend.tests.test_audit_evidence_export_api_unit`
- `backend.tests.test_compliance_review_package_api_unit`
- `backend.tests.test_gbz01_maintenance_unit`
- `backend.tests.test_emergency_change_api_unit`
- `backend.tests.test_retired_document_access_unit`
- `backend.tests.test_supplier_qualification_api_unit`
- `backend.tests.test_training_compliance_api_unit`
- `backend.tests.test_gbz01_compliance_gate_unit`
- `backend.tests.test_gbz02_compliance_gate_unit`
- `backend.tests.test_gbz03_compliance_gate_unit`
- `backend.tests.test_gbz04_compliance_gate_unit`
- `backend.tests.test_gbz05_compliance_gate_unit`
- `backend.tests.test_fda01_compliance_gate_unit`
- `backend.tests.test_fda02_compliance_gate_unit`
- `backend.tests.test_fda03_compliance_gate_unit`
- `backend.tests.test_r7_compliance_gate_unit`
- `fronted/e2e/tests/document.version-history.spec.js`
- `fronted/e2e/tests/admin.config-change-reason.spec.js`

## 3. 人工复核重点

- 受控文档根统一为 `docs/compliance/`
- 受控登记表引用路径与实际文件一致
- GMP 基线、周期复核状态和 residual gap 边界描述一致
- 退役、取证、审查包、培训、供应商评估和紧急变更文档均可在仓库内定位
