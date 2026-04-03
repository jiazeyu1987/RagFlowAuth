# 环境确认状态

版本: v1.0  
更新时间: 2026-04-03  
最后仓库复核日期: 2026-04-03  
下次仓库复核截止日期: 2026-10-03  
仓库内证据状态: complete  
仓库外证据状态: pending  
Residual gap 边界: 仓库内只覆盖供应商/组件确认主数据、版本变化再确认触发、环境 IQ/OQ/PQ 结果记录和审计留痕；线下供应商审核、签字版 IQ/OQ/PQ 协议/报告、基础设施资产编号与校准记录仍需在线下体系归档。  
IQ: `environment_qualification_records.iq_status` 记录安装鉴定结果，至少用于验证组件已按供应商规范安装。  
OQ: `environment_qualification_records.oq_status` 记录运行鉴定结果，至少用于验证关键配置和接口行为符合预期。  
PQ: `environment_qualification_records.pq_status` 记录性能鉴定结果，至少用于验证在当前预期用途下的性能和业务场景。  

## 1. 当前判断

- 已存在 `supplier_component_qualifications` 与 `environment_qualification_records` 两类仓库内记录。
- `current_version != approved_version` 时，系统会将组件状态切换为 `requalification_required`，阻断继续沿用旧批准版本。
- `tenant_database` 部署范围下，环境确认记录必须带 `company_id`，用于证明租户库环境确认与公司范围绑定。

## 2. 当前仓库内证据

| 类型 | 证据 |
|---|---|
| 表结构 | `backend/database/schema/supplier_qualification.py` |
| 服务 | `backend/services/supplier_qualification.py` |
| 接口 | `backend/app/modules/supplier_qualification/router.py` |
| 自动化测试 | `backend/tests/test_supplier_qualification_api_unit.py` |
| 门禁 | `backend/services/compliance/gbz04_validator.py`, `scripts/validate_gbz04_repo_compliance.py` |

## 3. 当前仓库内确认口径

- 供应商或组件确认基线通过 `/api/supplier-qualifications/components` 维护。
- 新版本变化通过 `/api/supplier-qualifications/components/{component_code}/version-change` 记录，并触发再确认。
- 环境 IQ/OQ/PQ 记录通过 `/api/supplier-qualifications/environment-records` 维护。
- 环境确认结果为 `approved` 时，至少要求 `IQ/OQ/PQ` 三项均为 `passed`。

## 4. 仓库外残余项

- 供应商现场审核报告和年度复评记录
- 线下签字版 IQ/OQ/PQ 协议、报告和偏差关闭记录
- 服务器/工作站/网络基础设施资产台账与校准证据
- 生产环境安装照片、设备编号和线下交接记录
