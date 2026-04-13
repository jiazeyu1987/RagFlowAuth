# PRD

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173900`
- Created: `2026-04-13T17:39:00`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS07-audit-and-evidence-export.md 开发 WS07：补齐统一审计事件、证据导出、全局搜索与智能对话留痕，并完成后端/前端/测试交付`

## Goal

让质量域审计体系真正覆盖 WS07 约定的关键留痕场景：后台能够以统一的 `QualityAuditEvent` 风格字段记录全局搜索、智能对话和文档调用证据，证据导出能携带这些事件及其关联资源，前台审计页能够检索和导出这些记录，最终形成可测试、可追溯、可导出的端到端实现。

## Scope

- 后端统一审计模型、查询和导出相关实现：
  - `backend/app/modules/audit/router.py`
  - `backend/database/schema/audit_logs.py`
  - `backend/services/audit/*`
  - `backend/services/audit_helpers.py`
  - `backend/services/audit_log_store.py`
  - `backend/app/modules/agents/router.py`
  - `backend/app/modules/chat/routes_completions.py`
  - 如有必要的 `backend/services/ragflow_chat_service.py`
- 前端审计与质量留痕相关页面和特性：
  - `fronted/src/features/audit/*`
  - `fronted/src/pages/AuditLogs.js`
  - `fronted/src/pages/Chat.js`
  - `fronted/src/pages/Agents.js`
- 针对上述变更补齐后端单测、前端单测，以及最终的浏览器级验证证据。

## Non-Goals

- 不修改 `fronted/src/routes/routeRegistry.js`、`fronted/src/shared/auth/capabilities.js`、`backend/app/core/permission_models.py`。
- 不把文控、培训、变更、设备、批记录等业务逻辑迁入审计模块，只为它们提供可复用的统一审计结构。
- 不新增用户未要求的 fallback、兼容分支、mock 成功路径或静默降级。
- 不扩展新的权限资源名或导航结构。

## Preconditions

- 本地 Python/pytest 可运行，能执行定向后端单测。
- `fronted/` 的 Node 依赖可用，能执行定向 React/Jest 测试。
- `data/auth.db` 或临时测试库 schema 可被 `ensure_schema` 正常初始化。
- 最终浏览器验证需要本地前后端可启动，且存在可登录的管理员账号、至少一个可见知识库以及一个可用聊天助手；若任一前提缺失，测试阶段必须 fail fast 并记录到 `task-state.json.blocking_prereqs`。

## Impacted Areas

- 审计事件 schema 与查询模型：现有 `audit_events` 表字段、`AuditLogStore.list_events` 返回形状、`AuditLogManager` 包装层。
- 搜索入口：`/api/search` 目前只返回检索结果，尚未进入质量审计事件体系。
- 对话入口：`/api/chats/{chat_id}/completions` 目前有流式日志和 citation sources 持久化，但缺少统一质量审计事件写入。
- 证据导出：当前 `AuditEvidenceExportService` 已导出审计/签名/审批/通知/备份数据，但尚未面向搜索/对话/文档调用场景组织统一证据引用。
- 审计页：当前 `AuditLogs` 仅支持有限过滤条件和只读列表，缺少对 WS07 新事件的检索与导出入口。
- 测试：需要补充后端 API/服务单测、前端 hook/page 单测，并在最终 tester 阶段提供真实浏览器证据。

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: 后端统一留痕与证据导出

- Objective:
  - 在不引入 fallback 的前提下，补齐全局搜索、智能对话、文档调用证据的统一审计记录，并让证据导出能够携带这些 WS07 事件。
- Owned paths:
  - `backend/app/modules/audit/router.py`
  - `backend/database/schema/audit_logs.py`
  - `backend/services/audit/manager.py`
  - `backend/services/audit/evidence_export.py`
  - `backend/services/audit_helpers.py`
  - `backend/services/audit_log_store.py`
  - `backend/app/modules/agents/router.py`
  - `backend/app/modules/chat/routes_completions.py`
  - `backend/tests/test_audit_events_api_unit.py`
  - `backend/tests/test_audit_evidence_export_api_unit.py`
  - `backend/tests/test_audit_log_manager_unit.py`
  - 新增或更新与 search/chat 留痕相关的后端测试文件
- Dependencies:
  - 现有 `audit_events` 表与 `ensure_schema` 可扩展
  - `ctx.deps` 中可解析审计 store/manager
  - 搜索和对话路由现有请求上下文可提供 request id、用户信息和数据集/会话信息
- Deliverables:
  - 统一审计事件结构对 search/chat/document invocation 生效
  - 搜索与对话场景的质量审计留痕
  - 证据导出中可见这些新事件及其证据引用
  - 对应后端单测

### P2: 前端审计工作台与可验证交付

- Objective:
  - 让管理员能在现有审计页面检索 WS07 新事件、触发证据导出，并在界面上看到搜索/对话/文档调用相关的关键上下文。
- Owned paths:
  - `fronted/src/features/audit/api.js`
  - `fronted/src/features/audit/api.test.js`
  - `fronted/src/features/audit/useAuditLogsPage.js`
  - `fronted/src/features/audit/useAuditLogsPage.test.js`
  - `fronted/src/pages/AuditLogs.js`
  - `fronted/src/pages/AuditLogs.test.js`
  - 如需要的 `fronted/src/pages/Chat.js`
  - 如需要的 `fronted/src/pages/Agents.js`
  - 如需要的新前端辅助测试文件
- Dependencies:
  - P1 暴露稳定的查询字段和导出接口
  - 现有 audit/chat/agents 页面结构保持不变
  - 不修改路由注册和权限资源名
- Deliverables:
  - 审计页可检索和导出 WS07 事件
  - 前端对新增事件字段有稳定展示
  - 对应前端单测

## Phase Acceptance Criteria

### P1

- P1-AC1: 后端存在单一、稳定的审计事件字段集合，能够承载搜索、对话、文档调用和证据引用场景，并继续以 `/api/audit/events` 输出稳定 JSON 结构。
- P1-AC2: `/api/search` 在成功检索时写入 `global_search` 领域事件，事件至少包含查询内容、目标数据集、分页参数、结果统计和请求上下文，且这些事件可被现有审计查询接口检索。
- P1-AC3: `/api/chats/{chat_id}/completions` 在完成对话时写入 `smart_chat` 领域事件，事件至少包含 chat/session/question 关键信息、回答关联来源或文档证据，并能被审计查询接口检索。
- P1-AC4: 审计证据导出结果中包含上述搜索/对话相关事件及其便携式 JSON/CSV 副本，manifest/checksum 仍保持可验证。
- P1-AC5: 后端单测覆盖新增的审计写入、查询和导出路径，并在缺少必要前提时显式失败而不是静默跳过。
- Evidence expectation:
  - `execution-log.md` 记录后端改动路径、执行的 pytest 命令、覆盖的 acceptance ids 和剩余风险。

### P2

- P2-AC1: 审计页支持查询 WS07 所需的关键字段组合，至少包括 source、event type 或 request/resource 维度中的新增检索能力，并可触发证据导出。
- P2-AC2: 审计页对搜索/对话/文档调用类事件展示可读的上下文摘要，不要求新增路由或权限资源名。
- P2-AC3: 前端测试覆盖新增 API、页面状态和交互行为，且不会破坏现有审计列表基础行为。
- Evidence expectation:
  - `execution-log.md` 记录前端改动路径、执行的 Jest 命令、覆盖的 acceptance ids 和剩余风险。

## Done Definition

- `P1`、`P2` 两个 phase 均完成并经 review gate 标记为 `completed`。
- `P1-AC1` 至 `P2-AC3` 全部有明确证据，证据落在 `execution-log.md` 和/或 `test-report.md`。
- 后端和前端定向测试均通过。
- 独立 tester 在真实浏览器中验证审计页能够检索到 WS07 相关事件并能触发导出，且给出非任务工件证据文件。
- `check_completion.py --apply` 通过后才能把任务标记为完成。

## Blocking Conditions

- `ctx.deps` 无法提供审计 store/manager，导致搜索或对话场景无法按统一审计结构落库。
- 审计 schema 变更无法通过 `ensure_schema` 初始化或破坏现有导出/查询契约。
- 前端依赖无法运行 Jest，或本地前后端无法启动到足以完成真实浏览器验证。
- 缺少管理员账号、知识库或聊天助手，导致无法完成真实运行态验证时，必须停止并记录阻塞原因，而不是用 mock 结果宣称完成。
