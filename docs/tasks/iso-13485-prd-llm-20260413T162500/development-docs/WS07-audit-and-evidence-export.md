# WS07：审计事件、证据导出与搜索/对话留痕

- Workstream ID: `WS07`
- 推荐 owner：后端主导，全栈配合
- 独立性：高

## 目标

统一质量域审计事件结构、证据附件结构和导出能力，并补齐源 PRD 中要求的全局搜索、智能对话、文档调用记录。

## 来源需求

- 源 PRD 问题项：`AUD-01`
- 源 PRD 章节：审计追踪与导出、整改实施路线图与治理中枢中的“审计与证据”

## 负责边界

- `QualityAuditEvent`
- 审计事件 schema
- 通用附件/证据引用结构
- 审计检索与导出页面
- 全局搜索与智能对话留痕

## 不负责范围

- 不负责文控、培训、变更、设备和批记录的业务逻辑本体。
- 不负责导航和权限资源名。

## 代码写入边界

后端 owner：

- `backend/app/modules/audit/*`
- `backend/database/schema/audit_logs.py`
- `backend/services/audit*`
- `backend/services/audit_helpers.py`
- `backend/services/ragflow_chat_service.py`

前端 owner：

- `fronted/src/features/audit/*`
- `fronted/src/pages/AuditLogs.js`
- `fronted/src/pages/DocumentAudit.js`
- `fronted/src/pages/Chat.js`
- `fronted/src/pages/Agents.js`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/shared/auth/capabilities.js`
- `backend/app/core/permission_models.py`

## 共享接口

本工作流拥有：

- `QualityAuditEvent`
- 通用附件/证据结构
- 审计事件字段与事件域命名

本工作流消费：

- `WS02` 的 `audit_events` 能力名与子路由
- 其他工作流发出的标准事件

## 依赖关系

- 可与 `WS01`、`WS02` 并行启动。
- 会被 `WS03`、`WS04`、`WS05`、`WS06`、`WS08` 消费。

## 验收标准

- 审计事件有统一字段和查询模型。
- 文控、培训、变更、设备、批记录可复用统一审计结构。
- 全局搜索、智能对话、文档调用留痕进入质量事件体系。
- 证据导出可关联附件、资源和事件。

## 交接给 LLM 的规则

1. 只定义通用审计结构与本工作流 own 的留痕场景。
2. 其他工作流在自己的模块里埋点，不把业务逻辑移到审计模块。
3. 若新增证据字段，先更新共享契约。
4. 不自行扩展权限资源名，统一消费 `WS02` 冻结值。
