# Operation Approval Follow-up Refactor Test Plan

- Task ID: `operation-approval-operationapprovalservice-help-20260408T064408`
- Created: `2026-04-08T06:44:08`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：在 operation_approval 域做第二轮局部重构，继续收敛后端 OperationApprovalService 剩余共享 helper 与历史死代码，同时拆分前端审批中心/审批配置 hook 的剩余混合职责，保持现有 API、页面行为和测试契约稳定。`

## Test Scope

Validate that the second-pass approval refactor preserves:

- backend approval service behaviour, approval router contracts, notification/migration flows, and
  state-machine regressions already covered by the focused approval suites
- frontend approval-center and approval-config hook/page behaviour, including query-param syncing,
  signature action handling, withdraw flow, workflow draft editing, and member search

Out of scope:

- unrelated notification-center, data-security, or document-preview regressions
- visual redesign or layout restyling checks outside the current approval pages
- broader end-to-end browser testing beyond the existing approval Jest coverage

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: local Python runtime with `pytest`
- Frontend: Node.js/npm with `react-scripts test` from `fronted/`

## Accounts and Fixtures

- backend tests rely on temporary SQLite databases, mocked approval handlers, mocked Ragflow service,
  local managed upload directories, and approval-domain service wiring
- frontend tests rely on mocked `operationApprovalApi`, mocked `usersApi`, mocked `useAuth`, and mocked `useSignaturePrompt`
- if Python or npm tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_operation_approval_service_unit.py backend/tests/test_operation_approval_router_unit.py backend/tests/test_operation_approval_notification_migration_unit.py -q`
  - Expected success signal: focused backend approval suites pass
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/operationApproval/useApprovalConfigPage.test.js src/features/operationApproval/useApprovalCenterPage.test.js src/pages/ApprovalConfig.test.js src/pages/ApprovalCenter.test.js`
  - Expected success signal: focused frontend approval suites pass

## Test Cases

### T1: Backend approval follow-up regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / route integration
- Command: `python -m pytest backend/tests/test_operation_approval_service_unit.py backend/tests/test_operation_approval_router_unit.py backend/tests/test_operation_approval_notification_migration_unit.py -q`
- Expected: helper extraction and dead-code removal preserve approval request creation, action flows, router contracts, and notification/migration behaviour

### T2: Frontend approval hook/page regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/operationApproval/useApprovalConfigPage.test.js src/features/operationApproval/useApprovalCenterPage.test.js src/pages/ApprovalConfig.test.js src/pages/ApprovalCenter.test.js`
- Expected: approval-center and approval-config hooks/pages keep current query handling, mutation flow, draft editing, and displayed behaviour

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend approval service | second-pass helper extraction preserves approval service and router behaviour | unit/route integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | frontend approval hooks/pages | hook decomposition preserves approval-center and approval-config behaviour | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. If a UI or interaction path is in scope, use a real browser or session and record concrete evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - backend approval service exports/contracts remain stable
  - frontend approval hooks/pages preserve current behaviour and test selectors
- Fail when:
  - either focused command fails
  - helper extraction changes approval API/router semantics, state-machine behaviour, or current approval page interactions

## Regression Scope

- `backend/services/operation_approval/*`
- `backend/app/modules/operation_approvals/router.py`
- `backend/tests/test_operation_approval_service_unit.py`
- `backend/tests/test_operation_approval_router_unit.py`
- `backend/tests/test_operation_approval_notification_migration_unit.py`
- `fronted/src/features/operationApproval/*`
- `fronted/src/pages/ApprovalCenter.js`
- `fronted/src/pages/ApprovalConfig.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record exact commands and whether each suite passed.
