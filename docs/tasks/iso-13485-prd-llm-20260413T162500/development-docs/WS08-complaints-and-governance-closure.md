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
