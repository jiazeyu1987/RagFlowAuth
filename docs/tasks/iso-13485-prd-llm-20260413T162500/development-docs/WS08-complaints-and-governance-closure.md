# WS08：投诉、CAPA、内审、管理评审与治理闭环

- Workstream ID: `WS08`
- 推荐 owner：后端主导，需求先行
- 独立性：中低

## 目标

承接源 PRD 中尚处于后续路线图阶段的治理闭环域，形成一个可独立开发但默认“需求待补足”的工作流文档，避免这些内容被遗漏或被错误塞入其他工作流。

## 来源需求

- 源 PRD 问题项：`PMS-01`
- 早期问题矩阵中涉及的 `CAPA`、供应商/环境确认相关内容
- 源 PRD 章节：投诉与持续改进、整改实施路线图 `R6`

## 负责边界

- `ComplaintCase`
- `CapaAction`
- `InternalAuditRecord`
- `ManagementReviewRecord`
- 与治理闭环相关的供应商/环境确认补充能力

## 不负责范围

- 不负责钉钉流程迁移。
- 不负责 Windchill / Teamcenter / 冠骋对标研究。
- 不负责设备、文控、培训、批记录主流程。

## 代码写入边界

现有可接管：

- `backend/app/modules/supplier_qualification/*`
- `backend/services/supplier_qualification.py`

允许新增后端：

- `backend/app/modules/complaints/*`
- `backend/app/modules/capa/*`
- `backend/app/modules/internal_audit/*`
- `backend/app/modules/management_review/*`
- `backend/services/complaints/*`
- `backend/services/capa/*`
- `backend/services/internal_audit/*`
- `backend/services/management_review/*`

允许新增前端：

- `fronted/src/features/complaints/*`
- `fronted/src/features/capa/*`
- `fronted/src/features/internalAudit/*`
- `fronted/src/features/managementReview/*`
- `fronted/src/pages/Complaints.js`
- `fronted/src/pages/InternalAudit.js`
- `fronted/src/pages/ManagementReview.js`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`

## 共享接口

本工作流拥有：

- `ComplaintCase`
- `CapaAction`
- `InternalAuditRecord`
- `ManagementReviewRecord`

本工作流消费：

- `WS02` 的能力名与子路由
- `WS07` 的审计事件结构
- `WS01` 的受控文件引用结构

## 依赖关系

- 依赖 `WS02`、`WS07`。
- 业务需求层面仍有明显上游缺口，需要在编码前补一轮需求冻结。

## 验收标准

- 文档明确区分“可以直接编码的部分”和“必须先补需求的部分”。
- 投诉、CAPA、内审、管理评审具备独立实体与边界，不再散落到其他工作流。
- 供应商/环境确认如需继续扩展，有明确 owner 和接入位置。

## 交接给 LLM 的规则

1. 默认这是一个“需求先行”的工作流，不要假设会议里未冻结的细节已经确定。
2. 不把钉钉迁移和外部软件对标研究直接当成功能编码任务。
3. 若上游未补需求，只能先产出更细需求稿，不直接写业务代码。

## 实施产出（2026-04-14）

本工作流已完成一轮“可执行最小闭环”实现，交付范围严格限定在 WS08 边界内：

- 后端实体与 API：
  - `ComplaintCase`
  - `CapaAction`
  - `InternalAuditRecord`
  - `ManagementReviewRecord`
- 数据库 schema：
  - `backend/database/schema/governance_closure.py`
- 模块路由：
  - `backend/app/modules/complaints/router.py`
  - `backend/app/modules/capa/router.py`
  - `backend/app/modules/internal_audit/router.py`
  - `backend/app/modules/management_review/router.py`
- 服务实现：
  - `backend/services/complaints/service.py`
  - `backend/services/capa/service.py`
  - `backend/services/internal_audit/service.py`
  - `backend/services/management_review/service.py`
  - `backend/services/governance_shared.py`
- 前端工作台：
  - `fronted/src/features/governanceClosure/GovernanceClosureWorkspace.js`
  - `fronted/src/features/governanceClosure/api.js`
  - 挂载到 `fronted/src/pages/QualitySystem.js` 的 `/quality-system/governance-closure` 子路由视图

## 已实现接口清单

- 投诉：
  - `POST /api/complaints/cases`
  - `GET /api/complaints/cases`
  - `POST /api/complaints/cases/{complaint_id}/assess`
  - `POST /api/complaints/cases/{complaint_id}/close`
- CAPA：
  - `POST /api/capa/actions`
  - `GET /api/capa/actions`
  - `POST /api/capa/actions/{capa_id}/verify`
  - `POST /api/capa/actions/{capa_id}/close`
- 内审：
  - `POST /api/internal-audits/records`
  - `GET /api/internal-audits/records`
  - `POST /api/internal-audits/records/{audit_id}/complete`
- 管理评审：
  - `POST /api/management-reviews/records`
  - `GET /api/management-reviews/records`
  - `POST /api/management-reviews/records/{review_id}/complete`

## 与其他工作流的契约遵守情况

- 未修改禁止文件：
  - `fronted/src/routes/routeRegistry.js`
  - `backend/app/core/permission_models.py`
  - `backend/app/modules/audit/*`
- 供应商/环境确认补充能力：
  - 投诉实体支持关联 `supplier_component_qualifications` 与 `environment_qualification_records`，并在创建时进行存在性校验。
- 审计事件结构消费：
  - WS08 模块通过 `audit_log_manager.log_ctx_event` 写入事件，保持与 WS07 统一审计模型兼容。

## 本轮验证命令

- `python -m pytest backend/tests/test_governance_closure_api_unit.py -q`
- `npm test -- --runInBand --watchAll=false src/pages/QualitySystem.test.js`

## 仍待上游冻结后再扩展的项

- 投诉闭环细则中的 SLA、分级升级规则、跨部门审批矩阵。
- CAPA 有效性评价的量化标准与判定窗口。
- 内审/管理评审模板字段与必填证据清单。
- WS02 未冻结 WS08 资源动作前，当前接口按 admin-only 执行。
