# 验证计划

版本: v1.2  
更新时间: 2026-04-03

## 1. 验证目标

验证 RagflowAuth 对 `R1-R10`、`FDA-02`、`FDA-03`、`GBZ-01`、`GBZ-02`、`GBZ-03`、`GBZ-04`、`GBZ-05` 的实现、测试证据和受控文档已达到可复核状态。

## 2. 范围

- 代码实现：权限、审批、通知、电子签名、水印、审计、文档版本受控、退役记录受控访问、供应商确认、培训与操作员认证、租户分库、备份恢复。
- 自动化测试：后端单测、前端关键 E2E、仓库内合规门禁脚本。
- 文档证据：`doc/compliance/`、`doc/test/`、门禁记录和验证报告。

## 3. 入场条件

- `P4-1` 与 `P4-2` 已通过。
- 后端与前端依赖可执行。
- 本次发布对应的受控文档已在 `controlled_document_register.md` 完成登记。

## 4. 通用通过准则

- 对应脚本或单元测试 `exit code = 0`。
- 追踪矩阵、验证报告、受控文档登记表与当前实现一致。
- 仓库外真实签字、纸质记录和外部介质活动如未完成，必须明确标记为 residual gap，不得在仓库内伪造为已完成。

## 5. FDA-03 审查包闭环验证

执行项：

- `python scripts/validate_fda03_repo_compliance.py --json`
- `python -m unittest backend.tests.test_compliance_review_package_api_unit backend.tests.test_fda03_compliance_gate_unit backend.tests.test_document_versioning_unit`
- `python -m unittest backend.tests.test_audit_events_api_unit`

通过准则：

- `validate_fda03_repo_compliance.py` 返回 `passed=true`，仅允许保留线下签字/真实发布批次归档类 residual gap。
- 审查包接口验证管理员导出、非管理员拒绝、manifest/checksum 存在、release version 对齐和审计留痕。

## 6. GBZ-01 Addendum

执行项：

- `python scripts/validate_gbz01_repo_compliance.py --json`
- `python -m unittest backend.tests.test_gbz01_maintenance_unit backend.tests.test_gbz01_compliance_gate_unit`

通过准则：

- `validate_gbz01_repo_compliance.py` 返回 `passed=true`。
- 测试覆盖维护影响评估、再确认触发器和旧验证结论阻断逻辑。

## 7. GBZ-02 Addendum

执行项：

- `python scripts/validate_gbz02_repo_compliance.py --json`
- `python -m unittest backend.tests.test_emergency_change_api_unit backend.tests.test_gbz02_compliance_gate_unit`

通过准则：

- `validate_gbz02_repo_compliance.py` 返回 `passed=true`。
- 测试覆盖先授权后部署、关闭前补齐复盘字段以及关键权限边界。

## 8. GBZ-03 Addendum

目标：

- 验证当前仓库内已落地的退役记录链路满足“退役后保留期内可访问”的最小闭环。
- 验证受控文档沿用现有 `retired_records` 路径，不新建第二套退役系统。

仓库内实现证据：

- `backend/services/compliance/retired_records.py`
- `backend/app/modules/knowledge/routes/retired.py`
- `backend/app/modules/audit/router.py`

测试证据：

- `python scripts/validate_gbz03_repo_compliance.py --json`
- `python -m unittest backend.tests.test_retired_document_access_unit`
- `python -m unittest backend.tests.test_gbz03_compliance_gate_unit`

文档复核项：

- `doc/compliance/release_and_retirement_sop.md`
- `doc/compliance/retirement_plan.md`
- `doc/compliance/retirement_archive_status.md`
- `doc/compliance/controlled_document_register.md`
- `doc/compliance/urs.md`
- `doc/compliance/srs.md`
- `doc/compliance/traceability_matrix.md`
- `doc/compliance/validation_report.md`

通过准则：

- `validate_gbz03_repo_compliance.py` 已纳入 GBZ-03 仓库内门禁口径，实际结果以现场执行输出为准。
- `backend.tests.test_retired_document_access_unit` 通过。
- `backend.tests.test_gbz03_compliance_gate_unit` 纳入 GBZ-03 门禁测试集合。
- 文档证据仅指向 `retired_records.py`、`retired.py`、`audit/router.py`、`test_retired_document_access_unit.py` 这一条现行实现路径。
- 仓库外纸质批准、介质封存、保留期届满后的线下处置仍明确标记为 residual gap。

## 9. GBZ-04 Addendum

目标：

- 验证系统已形成供应商/现成软件确认基线、版本变化再确认触发和环境级 IQ/OQ/PQ 记录的最小仓库内闭环。
- 验证租户数据库环境确认必须绑定 `company_id`，且组件版本变化后不能继续沿用旧批准状态。

仓库内实现证据：

- `backend/database/schema/supplier_qualification.py`
- `backend/services/supplier_qualification.py`
- `backend/app/modules/supplier_qualification/router.py`

测试证据：

- `python scripts/validate_gbz04_repo_compliance.py --json`
- `python -m unittest backend.tests.test_supplier_qualification_api_unit backend.tests.test_gbz04_compliance_gate_unit`

文档复核项：

- `doc/compliance/supplier_assessment.md`
- `doc/compliance/environment_qualification_status.md`
- `doc/compliance/controlled_document_register.md`
- `doc/compliance/urs.md`
- `doc/compliance/srs.md`
- `doc/compliance/traceability_matrix.md`
- `doc/compliance/validation_report.md`

通过准则：

- `validate_gbz04_repo_compliance.py` 返回 `passed=true`，仅允许保留线下供应商审核和签字版 IQ/OQ/PQ 记录类 residual gap。
- `backend.tests.test_supplier_qualification_api_unit` 覆盖非管理员拒绝、版本变化触发 `requalification_required`、`tenant_database` 必须带 `company_id`、happy path 与审计留痕。
- `backend.tests.test_gbz04_compliance_gate_unit` 覆盖 gate 通过与追踪映射缺失阻断。

## 10. GBZ-05 Addendum

目标：

- 验证系统已形成受控培训要求、培训记录、培训有效性评价和操作员认证的最小仓库内闭环。
- 验证 `document_review` 与 `restore_drill_execute` 已接入真实门禁，且培训版本变化后必须重新培训再上岗。

仓库内实现证据：

- `backend/database/schema/training_compliance.py`
- `backend/services/training_compliance.py`
- `backend/app/core/training_support.py`
- `backend/app/modules/training_compliance/router.py`
- `backend/app/modules/review/routes/approve.py`
- `backend/app/modules/review/routes/reject.py`
- `backend/app/modules/review/routes/overwrite.py`
- `backend/app/modules/data_security/router.py`

测试证据：

- `python scripts/validate_gbz05_repo_compliance.py --json`
- `python -m unittest backend.tests.test_training_compliance_api_unit backend.tests.test_gbz05_compliance_gate_unit`
- `python -m unittest backend.tests.test_review_assignment_integration_unit backend.tests.test_review_signature_integration backend.tests.test_review_audit_integration backend.tests.test_review_notification_integration_unit backend.tests.test_backup_restore_audit_unit`

文档复核项：

- `doc/compliance/training_matrix.md`
- `doc/compliance/training_operator_qualification_status.md`
- `doc/compliance/controlled_document_register.md`
- `doc/compliance/urs.md`
- `doc/compliance/srs.md`
- `doc/compliance/traceability_matrix.md`
- `doc/compliance/validation_report.md`

通过准则：

- `validate_gbz05_repo_compliance.py` 返回 `passed=true`，仅允许保留线下培训签到、考试签字和例外放行归档类 residual gap。
- `backend.tests.test_training_compliance_api_unit` 覆盖非管理员拒绝、培训记录与认证 happy path、`curriculum_version` 变化后旧培训失效，以及认证过期阻断恢复演练。
- 受影响的审批/恢复演练回归测试通过，确认新增门禁未破坏既有审计、通知、签名和恢复演练路径。

## 11. 证据输出

- `doc/compliance/validation_report.md`
- `doc/compliance/traceability_matrix.md`
- `doc/compliance/retirement_archive_status.md`
- `doc/compliance/environment_qualification_status.md`
- `doc/compliance/training_operator_qualification_status.md`
