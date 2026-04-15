# Execute WS06: Document Control Frontend Workspace Test Plan

- Task ID: `execute-ws06-document-control-frontend-workspace-20260414T223245`
- Created: `2026-04-14T22:32:45`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws06-document-control-frontend-workspace.md 下的前端工作`

## Test Scope

验证文控页面已从“直接状态跳转”切换为“工作区 + 显式动作”模式，并且：

- 不再存在 legacy `Move to ...` 按钮或 `/transitions` 调用
- 审批区块能展示审批阶段/待处理人，并能触发 submit/approve/reject/add-sign 动作（基于稳定合同）
- 培训/发布/部门确认/留存区块在合同可用时能渲染真实状态；缺少输入时前端 fail-fast 提示
- capability/`PermissionGuard` 的显隐逻辑仍然有效（至少不破坏已有 guard 测试）

## Environment

- Windows / PowerShell
- Node + npm
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Frontend cwd: `D:\ProjectPackage\RagflowAuth\fronted`

## Accounts and Fixtures

本任务以前端单测为主：

- Jest tests 使用 mock API，不依赖真实后端账号
- 若需要手工 spot-check，使用可登录账号并具备 `document_control` 权限

缺少 Node/npm 或无法运行 Jest 则必须 fail-fast 并记录缺失前提。

## Commands

- `Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'`
- `$env:CI='true'`
- `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js PermissionGuard.test.js`
  - Success signal: 0 exit code，且三份测试文件全部通过

（补充）若本次改动涉及 API contract 单测：

- `npm test -- --watch=false --runInBand api.test.js`
  - Success signal: documentControl API 单测通过

## Test Cases

### T1: Legacy transitions removed

- Covers: P1-AC1
- Level: unit (react-testing-library)
- Command: `npm test -- --watch=false --runInBand DocumentControl.test.js`
- Expected: 页面不再出现 `Move to` 按钮，且任何交互不触发 `/transitions` 或 `transitionRevision`。

### T2: Approval workspace renders and actions are wired

- Covers: P1-AC2, P2-AC1, P2-AC2
- Level: unit (react-testing-library) + hook unit
- Command: `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js`
- Expected: `approval_request_id` 存在时可渲染步骤/待处理人，并且 Submit/Approve/Reject/Add-sign 均调用显式动作 API 且更新成功提示。

### T3: Training / release / dept-ack / retention sections surface real state

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: unit (hook) + shallow UI assertions
- Command: `npm test -- --watch=false --runInBand useDocumentControlPage.test.js`
- Expected: Training/Release/Dept Ack/Retention 区块使用真实合同字段渲染；输入缺失时前端 fail-fast，不发起隐式默认请求。

### T4: Guard regressions

- Covers: P2-AC2
- Level: unit
- Command: `npm test -- --watch=false --runInBand PermissionGuard.test.js`
- Expected: `PermissionGuard.test.js` 通过，且本任务没有破坏 guard 行为。

### T5: Validation command passes

- Covers: P4-AC1
- Level: integration (test runner)
- Command: `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js PermissionGuard.test.js`
- Expected: 命令通过且所有用例通过（0 exit code）。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | DocumentControl | 移除 legacy transitions | unit | P1-AC1 | `test-report.md#T1` |
| T2 | Approval workspace | 渲染审批状态 + 动作接线 | unit | P1-AC2, P2-AC1, P2-AC2 | `test-report.md#T2` |
| T3 | Workflow sections | 培训/发布/部门确认/留存状态 | unit | P3-AC1, P3-AC2, P3-AC3 | `test-report.md#T3` |
| T4 | PermissionGuard | guard 回归验证 | unit | P2-AC2 | `test-report.md#T4` |
| T5 | Validation | 指定验证命令通过 | integration | P4-AC1 | `test-report.md#T5` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, Node/npm, Jest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 以真实 repo 结构为准，不允许通过 mock 数据“伪造完成”。
- Escalation rule: 若发现 UI 仍调用 legacy `/transitions` 或出现 mock 成功态/兜底分支，直接判定失败并回传缺陷。

## Pass / Fail Criteria

- Pass when:
  - `P1`-`P4` 覆盖的测试全部通过，且页面不再暴露 legacy transitions
  - 关键动作均映射到显式后端动作接口（mock 可验证）
- Fail when:
  - 仍存在任何 `Move to ...` 或 `/transitions` 调用
  - 需要引入 fallback / mock 成功态才能让页面通过测试

## Regression Scope

- `fronted/src/pages/DocumentControl.js` 页面渲染结构与 data-testid
- `fronted/src/features/documentControl/useDocumentControlPage.js` 过滤/加载/创建逻辑
- `fronted/src/shared/errors/userFacingErrorMessages.js` 对已有错误码的映射不应被破坏

## Reporting Notes

结果写入 `test-report.md`，包含命令、通过/失败、以及关键 evidence（至少引用测试输出摘要）。
