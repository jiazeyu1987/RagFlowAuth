# 验证报告

版本: v1.2  
更新时间: 2026-04-03

## 1. 执行摘要

本轮验证覆盖仓库内已落地的合规控制与受控文档一致性。当前已形成仓库内闭环并具备自动化验证证据的条目包括：`R7`、`FDA-03`、`GBZ-01`、`GBZ-02`、`GBZ-03`、`GBZ-04`、`GBZ-05`。

## 2. 已有验证记录

| 类别 | 命令 | 结果 |
|---|---|---|
| R7 门禁 | `python scripts/validate_r7_repo_compliance.py --json` | 通过，`passed=true`，`blocking_issues=[]`，保留 `external_evidence_pending` 提示 |
| R7 后端 | `python -m unittest backend.tests.test_r7_compliance_gate_unit backend.tests.test_document_versioning_unit backend.tests.test_config_change_log_unit` | 通过 |
| R7 前端 | `cd fronted; npx playwright test e2e/tests/document.version-history.spec.js e2e/tests/admin.config-change-reason.spec.js --workers=1` | 通过 |
| FDA-03 门禁 | `python scripts/validate_fda03_repo_compliance.py --json` | 通过，`passed=true`，`blocking_issues=[]`，仅保留 `external_release_signoff_pending` |
| FDA-03 后端 | `python -m unittest backend.tests.test_compliance_review_package_api_unit backend.tests.test_fda03_compliance_gate_unit backend.tests.test_document_versioning_unit` | 通过 |
| FDA-03 审计 | `python -m unittest backend.tests.test_audit_events_api_unit` | 通过 |
| GBZ-01 门禁 | `python scripts/validate_gbz01_repo_compliance.py --json` | 通过，`passed=true`，`blocking_issues=[]`，仅保留 `external_maintenance_evidence_pending` |
| GBZ-01 后端 | `python -m unittest backend.tests.test_gbz01_maintenance_unit backend.tests.test_gbz01_compliance_gate_unit` | 通过 |
| GBZ-02 门禁 | `python scripts/validate_gbz02_repo_compliance.py --json` | 通过，`passed=true`，`blocking_issues=[]`，仅保留 `external_emergency_change_execution_pending` |
| GBZ-02 后端 | `python -m unittest backend.tests.test_emergency_change_api_unit backend.tests.test_gbz02_compliance_gate_unit` | 通过 |
| GBZ-04 后端 | `python -m unittest backend.tests.test_supplier_qualification_api_unit backend.tests.test_gbz04_compliance_gate_unit` | 通过 |

## 3. GBZ-03 当前验证范围

GBZ-03 本轮只基于当前已接入主链路的退役记录实现建立仓库内证据，不新增第二套退役系统。纳入验证的实现与证据如下：

- `backend/services/compliance/retired_records.py`
- `backend/app/modules/knowledge/routes/retired.py`
- `backend/app/modules/audit/router.py`
- `backend/tests/test_retired_document_access_unit.py`

## 4. GBZ-03 预期覆盖点

- 已批准文档可被退役，并生成退役文件副本、manifest、checksums 和记录包。
- 常规文档下载入口在退役后拒绝访问，强制切换到退役记录入口。
- 已授权业务用户可在保留期内查询、预览、下载退役文件。
- 管理员可查询退役记录清单并导出记录包。
- 退役、下载、导出动作写入审计日志。

## 5. GBZ-03 执行记录

| 类别 | 命令 | 结果 |
|---|---|---|
| GBZ-03 门禁 | `python scripts/validate_gbz03_repo_compliance.py --json` | 通过，`passed=true`，`blocking_issues=[]`，保留 `external_retirement_archive_records_pending` 作为仓库外残余项编码 |
| GBZ-03 后端 | `python -m unittest backend.tests.test_retired_document_access_unit` | 通过，`Ran 3 tests in 0.500s`，`OK` |
| GBZ-03 门禁单测 | `python -m unittest backend.tests.test_gbz03_compliance_gate_unit` | 通过，`Ran 2 tests in 0.057s`，`OK` |

GBZ-03 本轮通过点：

- 覆盖退役、授权用户访问、未授权用户拒绝、保留期过期返回 `410`、管理员记录包导出与审计留痕。
- 受控文档已统一切换到 `retired_records.py`、`retired.py`、`audit/router.py`、`test_retired_document_access_unit.py` 这一条实现路径。
- `validate_gbz03_repo_compliance.py` 已通过，当前不存在仓库内 blocking issue；`external_retirement_archive_records_pending` 仅表示仓库外退役归档记录仍待补齐，而非仓库内已造假完成。

## 6. GBZ-03 仓库外残余项

以下事项未在仓库内被伪造为“已完成”，仍需在线下或外部受控体系保留：

- 纸质退役审批和签字页
- 介质封存、移交或长期保管记录
- 保留期届满后的销毁或移交签字
- 长期可读性抽检与法规年限确认记录

## 7. GBZ-04 执行记录

范围：

- 供应商/现成软件确认主数据
- 版本变化触发再确认
- 环境级 IQ/OQ/PQ 记录与租户数据库 `company_id` 绑定
- `validate_gbz04_repo_compliance.py` 仓库门禁

实际结果：

- `python -m unittest backend.tests.test_supplier_qualification_api_unit backend.tests.test_gbz04_compliance_gate_unit` 已执行，结果 `Ran 6 tests ... OK`。
- `python scripts/validate_gbz04_repo_compliance.py --json` 已执行，结果 `passed=true`、`blocking_issues=[]`，仅保留 `external_supplier_qualification_records_pending`。

本轮通过点：

- 已新增供应商/现成软件确认与环境确认持久化模型，不再仅依赖静态文档说明。
- 版本变化会触发 `requalification_required`，避免继续沿用旧批准版本。
- `tenant_database` 的环境确认必须带 `company_id`，能够把租户库确认记录与公司范围绑定。

仓库外残余项代码：

- `external_supplier_qualification_records_pending`

线下仍需补齐：

- 供应商现场审核报告和年度复评记录
- 签字版 IQ/OQ/PQ 协议、报告和偏差关闭记录
- 基础设施资产编号、校准和安装照片等环境级证据

## 8. GBZ-05 执行记录

范围：

- 受控培训要求、培训记录、培训有效性评价
- 操作员认证、复训到期控制
- `document_review` 与 `restore_drill_execute` 门禁
- `validate_gbz05_repo_compliance.py` 仓库门禁

实际结果：

- `python -m unittest backend.tests.test_training_compliance_api_unit backend.tests.test_gbz05_compliance_gate_unit backend.tests.test_review_assignment_integration_unit backend.tests.test_review_signature_integration backend.tests.test_review_audit_integration backend.tests.test_review_notification_integration_unit backend.tests.test_backup_restore_audit_unit` 已执行，结果 `Ran 18 tests ... OK`。
- `python scripts/validate_gbz05_repo_compliance.py --json` 已执行，结果 `passed=true`、`blocking_issues=[]`，仅保留 `external_training_qualification_records_pending`。

本轮通过点：

- 系统新增 `training_requirements`、`training_records`、`operator_certifications` 三类持久化记录，不再只停留在职责矩阵文档。
- `curriculum_version` 变化后，旧培训记录和旧操作员认证不能继续用于关键动作。
- 审批/驳回/覆盖审批与恢复演练已接入统一培训门禁，未培训、有效性未通过或认证过期时将被系统阻断。

仓库外残余项代码：

- `external_training_qualification_records_pending`

线下仍需补齐：

- 培训签到表和纸质考试签字页
- 岗位资格矩阵批准页
- 例外放行审批单和偏差关闭记录

仓库内门禁校验不替代线下签字和真实培训执行记录。
