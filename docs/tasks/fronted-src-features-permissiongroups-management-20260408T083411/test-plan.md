# Permission Group Management Hook Refactor Test Plan

- Task ID: `fronted-src-features-permissiongroups-management-20260408T083411`
- Created: `2026-04-08T08:34:11`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/features/permissionGroups/management/usePermissionGroupManagement.js，拆分初始化加载、目录/权限组选择与模式切换、权限组与文件夹变更动作、拖拽移动等共享逻辑，保持 usePermissionGroupManagementPage 和现有 Jest 行为稳定`

## Test Scope

Validate that the bounded hook refactor preserves:

- initial bootstrapping through `permissionGroupsApi` and hidden-chat filtering
- page-facing derived data such as folder path and dataset items
- page-hook and page-level consumers that depend on the existing return contract

Out of scope:

- real browser drag-and-drop behavior
- live backend integration against a running permission service
- unrelated permission, user, or knowledge management pages

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend runtime: CRA/Jest via `npm test`
- Test runtime: mocked `permissionGroupsApi`, mocked page hook consumers, and focused hook/page
  suites already in the repo

## Accounts and Fixtures

- tests rely on mocked API responses and mocked child components
- no live backend, browser automation, or seeded database is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/permissionGroups/management/usePermissionGroupManagement.test.js src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js src/pages/PermissionGroupManagement.test.js`
  - Expected success signal: all focused permission-group hook, page-hook, and page suites pass in
    one non-watch run

## Test Cases

### T1: Permission group hook and page regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/permissionGroups/management/usePermissionGroupManagement.test.js src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js src/pages/PermissionGroupManagement.test.js`
- Expected: the refactored hook preserves current bootstrapping, derived state, and page-facing
  contract without breaking existing page-hook or page behavior

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend permission group management | hook decomposition preserves current loading, derived state, and consumer wiring | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused Jest command against the real repo state in
  `fronted/`
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the focused Jest command succeeds
  - the current hook/page contract remains compatible with the existing tests
- Fail when:
  - the command fails
  - the refactor changes required return keys, breaks initial selection, or breaks page/page-hook
    integration

## Regression Scope

- `fronted/src/features/permissionGroups/management/usePermissionGroupManagement.js`
- new helper module(s) or child hook(s) under
  `fronted/src/features/permissionGroups/management/`
- `fronted/src/features/permissionGroups/management/usePermissionGroupManagementPage.js`
- `fronted/src/pages/PermissionGroupManagement.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command, whether it passed, and any remaining risk around uncovered drag/drop
  interaction branches.
