# 验证报告

版本: v1.0
更新时间: 2026-04-14

## 1. 仓库内门禁校验

- FDA-01：`validate_fda01_repo_compliance.py`
- FDA-02：`validate_fda02_repo_compliance.py`
- FDA-03：`validate_fda03_repo_compliance.py`
- GBZ-01：`validate_gbz01_repo_compliance.py`
- GBZ-02：`validate_gbz02_repo_compliance.py`
- GBZ-03：`validate_gbz03_repo_compliance.py`
- GBZ-04：`validate_gbz04_repo_compliance.py`
- GBZ-05：`validate_gbz05_repo_compliance.py`
- R7：`validate_r7_repo_compliance.py`

## 2. 结论摘要

- FDA-03：受控文档登记与审查包导出链路作为仓库内证据保留。
- GBZ-01：维护影响判定链路与门禁脚本纳入仓库内一致性复核，保留 residual gap 边界说明。
- GBZ-02：紧急变更链路保留 `external_emergency_change_execution_pending` 作为仓库外残余项标识。
- GBZ-03：退役归档链路保留 `external_retirement_archive_records_pending` 作为仓库外残余项标识。
- GBZ-04：供应商与环境确认链路保留 `external_supplier_qualification_records_pending` 作为仓库外残余项标识。
- GBZ-05：培训与上岗资格链路保留 `external_training_qualification_records_pending` 作为仓库外残余项标识。
- R7：仓库内门禁校验只证明文档、映射、测试与周期复核状态一致，不替代线下签字、真实环境执行和管理层批准记录。

## 3. 自动化与文档复核证据

- `backend.tests.test_operation_approval_service_unit`
- `backend.tests.test_electronic_signature_unit`
- `backend.tests.test_audit_evidence_export_api_unit`
- `backend.tests.test_compliance_review_package_api_unit`
- `backend.tests.test_gbz01_maintenance_unit`
- `backend.tests.test_retired_document_access_unit`
- `backend.tests.test_supplier_qualification_api_unit`
- `backend.tests.test_training_compliance_api_unit`
- `backend.tests.test_r7_compliance_gate_unit`
