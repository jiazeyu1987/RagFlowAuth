# Execute WS06: Document Control Frontend Workspace PRD

- Task ID: `execute-ws06-document-control-frontend-workspace-20260414T223245`
- Created: `2026-04-14T22:32:45`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws06-document-control-frontend-workspace.md 下的前端工作`

## Goal

把 `fronted/src/pages/DocumentControl.js` 从“直接暴露状态跳转按钮”升级为工作区式页面：

- 前端不再展示或调用遗留的“Move to …”状态跳转
- 前端通过稳定后端合同展示审批、培训门禁、发布/分发（以现有 change-control 合同为主）、部门确认、作废/留存信息
- 页面动作只调用显式业务动作接口（提交审批/审批通过/驳回/加签等），并保持 capability/`PermissionGuard` 可见性约束

## Scope

- Frontend: `fronted/src/pages/DocumentControl.js`
- Frontend feature: `fronted/src/features/documentControl/*`
- Frontend errors: `fronted/src/shared/errors/userFacingErrorMessages.js`
- Frontend tests:
  - `fronted/src/pages/DocumentControl.test.js`
  - `fronted/src/features/documentControl/useDocumentControlPage.test.js`
  - `fronted/src/features/documentControl/api.test.js`

## Non-Goals

- 不设计或改写后端流程语义（审批矩阵/培训门禁计算/发布台账建模/部门确认模型/销毁调度逻辑）
- 不引入兼容分支、mock 数据或“先沿用旧流程”的 fallback
- 不把 `fronted/`、`docs/maintance/` 等现有目录名“顺手纠正”成理想命名

## Preconditions

必须存在且可用的后端合同（缺失则停止执行并记录到 `task-state.json.blocking_prereqs`）：

- 文控读接口：
  - `GET /api/quality-system/doc-control/documents`
  - `GET /api/quality-system/doc-control/documents/{controlled_document_id}`
- 审批动作接口（替代 legacy transitions）：
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/approval/submit`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/approval/approve`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/approval/reject`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/approval/add-sign`
- 审批详情查询（用于展示步骤/待处理人）：
  - `GET /api/operation-approvals/requests/{request_id}`
- 培训接口（用于展示/触发培训相关信息）：
  - `GET /api/training-compliance/assignments`
  - `POST /api/training-compliance/assignments/generate`
- 发布/分发与部门确认（现有 change-control 合同）：
  - `GET /api/change-control/requests`
- 作废/留存信息（现有 retired-documents 合同）：
  - `GET /api/retired-documents`

工具链：

- Node/npm 可用，能在 `D:\ProjectPackage\RagflowAuth\fronted` 下运行 Jest

## Impacted Areas

- Document control page contracts: `fronted/src/features/documentControl/api.js`
- Permission visibility: `fronted/src/components/PermissionGuard.js`, `fronted/src/hooks/useAuth.js` (read-only usage)
- Related modules/APIs (read-only reuse):
  - `fronted/src/features/operationApproval/api.js`
  - `fronted/src/features/trainingCompliance/api.js`
  - `fronted/src/features/changeControl/api.js`
- User-facing error mapping: `fronted/src/shared/errors/userFacingErrorMessages.js`

## Phase Plan

### P1: Remove legacy transitions and wire approval actions

- Objective: 移除 UI 中的 “Move to …” 行为，并将页面动作映射到后端审批动作接口。
- Owned paths:
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/features/documentControl/api.js`
  - `fronted/src/features/documentControl/useDocumentControlPage.js`
- Dependencies: none
- Deliverables:
  - `transitionRevision` 从前端 contract 中移除
  - 新增 submit/approve/reject/add-sign API + hook handlers

### P2: Add approval workspace section (contract-driven)

- Objective: 渲染审批阶段、当前步骤、待处理人，并用 capability 控制动作可见性。
- Owned paths:
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/features/documentControl/useDocumentControlPage.js`
- Dependencies: P1
- Deliverables:
  - Approval 区块展示审批摘要 +（在有 `approval_request_id` 时）加载审批详情
  - 显式阻断提示（失败时展示可读错误，不伪造成功）

### P3: Render training / release / department-ack / retention sections

- Objective: 在同一工作区展示培训、发布/分发（基于 change-control）、部门确认（基于 change-control confirmations）、作废/留存（基于 retired-documents）信息。
- Owned paths:
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/features/documentControl/useDocumentControlPage.js`
  - `fronted/src/features/documentControl/api.js`
- Dependencies: P2
- Deliverables:
  - Training 区块：展示与当前修订相关的“我”的培训任务（若可获取），并提供生成培训动作（显式输入 assignee）
  - Release/Dept Ack 区块：展示与当前修订关联的 change-control request 与 confirmations
  - Retention 区块：若存在 retired record，展示 retention_until 等字段

### P4: Update tests and validate

- Objective: 用聚焦测试覆盖核心交互，确保 page 不再有 legacy 行为，并通过指定测试命令。
- Owned paths:
  - `fronted/src/pages/DocumentControl.test.js`
  - `fronted/src/features/documentControl/useDocumentControlPage.test.js`
  - `fronted/src/features/documentControl/api.test.js`
  - `fronted/src/shared/errors/userFacingErrorMessages.js`
- Dependencies: P3
- Deliverables:
  - Jest tests updated
  - Validation command passes

## Phase Acceptance Criteria

### P1

- P1-AC1: 页面不再渲染任何 `Move to ...` 状态跳转按钮，也不再调用 `/revisions/{id}/transitions`。
- P1-AC2: `documentControlApi` 提供 `submitRevisionForApproval` / `approveRevisionStep` / `rejectRevisionStep` / `addSignRevisionStep` 并有 API 单测覆盖 URL 与 envelope 解析。
- Evidence expectation: `fronted/src/features/documentControl/api.test.js` 更新 + 相关 mock 调用断言通过。

### P2

- P2-AC1: 当修订存在 `approval_request_id` 时，工作区展示当前步骤与待处理审批人（来自 `operation-approvals/requests/{id}`）。
- P2-AC2: Submit/Approve/Reject/Add-sign 按钮的显隐与禁用基于 capability/状态，不出现“假按钮”。
- Evidence expectation: `DocumentControl.test.js` 覆盖审批区块渲染与动作触发。

### P3

- P3-AC1: Training 区块展示与当前修订相关的培训状态；生成培训动作缺少 assignee 时前端 fail-fast 并提示。
- P3-AC2: Release/Dept Ack 区块展示关联的 change-control requests，并展示 confirmations 状态摘要。
- P3-AC3: Retention 区块在可用时展示 retired record 的留存信息（至少 `retention_until_ms`）。
- Evidence expectation: `useDocumentControlPage.test.js` 覆盖 state 派生 + 错误分支。

### P4

- P4-AC1: 下述命令通过：
  - `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js PermissionGuard.test.js`
- Evidence expectation: `test-report.md` 记录命令与通过结果。

## Done Definition

- “Move to …” legacy 行为在 UI 和 `documentControlApi` 中完全移除
- DocumentControl 页面包含并渲染以下用户可见区块（按 capability 控制展示）：
  - Approval
  - Training
  - Release / Department Acknowledgment
  - Obsolete / Retention
- 关键前端测试通过，并在 `execution-log.md` / `test-report.md` 中有证据记录

## Blocking Conditions

- 任一前置后端合同缺失或返回 payload shape 不符合约定（不得通过 mock/placeholder 绕过）
- 只能通过“恢复 legacy transitions”才能让 UI 可用的情况（禁止）
