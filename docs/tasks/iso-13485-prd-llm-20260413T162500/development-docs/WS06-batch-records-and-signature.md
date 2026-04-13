# WS06：批记录模板、执行与电子签名

- Workstream ID: `WS06`
- 推荐 owner：全栈
- 独立性：中

## 目标

实现源 PRD 中的生产/检验批记录电子化能力，包括模板版本管理、实时记录、现场拍照、签名确认和导出。

## 来源需求

- 源 PRD 问题项：`BR-01`
- 源 PRD 章节：批记录管理、建议的核心台账/实体、整改实施路线图 `R5`

## 负责边界

- `BatchRecordTemplate`
- `BatchRecordExecution`
- 模板版本受控、执行实例、字段填写、照片证据、签名确认、审阅导出

## 不负责范围

- 不负责通用权限模型。
- 不负责通用审计 schema。
- 不负责文控和培训流程。

## 代码写入边界

允许新增后端：

- `backend/app/modules/batch_records/*`
- `backend/services/batch_records/*`

允许新增前端：

- `fronted/src/features/batchRecords/*`
- `fronted/src/pages/BatchRecords.js`

有限可改：

- `backend/app/modules/electronic_signature/routes/challenge.py`
- `fronted/src/features/operationApproval/useSignaturePrompt.js`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`

## 共享接口

本工作流拥有：

- `BatchRecordTemplate`
- `BatchRecordExecution`
- 批记录字段级签名和审阅规则

本工作流消费：

- `WS02` 的 `batch_records` 能力名与子路由
- `WS07` 的附件/证据结构与审计字段
- 现有电子签名挑战能力

## 依赖关系

- 依赖 `WS02` 提供入口和权限。
- 依赖 `WS07` 冻结证据与审计结构。

## 验收标准

- 模板支持版本管理。
- 执行记录支持实时填写，不能事后冒充实时。
- 支持现场拍照上传。
- 支持手签加口令或统一电子签名策略。
- 导出结果包含执行记录、照片、签名和审计痕迹。

## 交接给 LLM 的规则

1. 只在批记录或电子签名适配层修改，不接手其他工作流页面。
2. 照片、附件、导出结构必须复用 `WS07` 契约。
3. 若电子签名能力不足，先补适配，不直接改管理端主逻辑。
4. 入口与权限接入由 `WS02` 统一完成。
