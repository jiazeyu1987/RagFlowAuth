# Permission Group Management Page Refactor Test Plan

- Task ID: `tranche-fronted-src-pages-permissiongroupmanagem-20260408T082611`
- Created: `2026-04-08T08:26:11`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/pages/PermissionGroupManagement.js锛屾媶鍒嗗伐鍏锋爮銆佹枃浠跺す鏍戜晶杈广€佺姸鎬佷笌鍒犻櫎纭鍖哄煙銆佺紪杈戝櫒闈㈡澘绛夐〉闈㈠尯鍧楋紝淇濇寔 usePermissionGroupManagementPage 濂戠害涓庣幇鏈?Jest 娴嬭瘯琛屼负绋冲畾`

## Test Scope

Validate that the bounded frontend refactor preserves:

- `usePermissionGroupManagementPage` hook-level delete-confirmation and editable-folder behavior
- `PermissionGroupManagement` page toolbar behavior and disabled states
- the page-facing hook contract consumed by the route page

Out of scope:

- real-browser drag-and-drop
- live permission-group backend integration
- refactoring the underlying `usePermissionGroupManagement` hook

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend: CRA/Jest via `npm test`
- Test runtime: mocked page hook, folder tree, and editor form embedded in the focused Jest suites

## Accounts and Fixtures

- tests rely on mocked `usePermissionGroupManagementPage` and mocked child components
- no live backend, browser automation, or seed data is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js src/pages/PermissionGroupManagement.test.js`
  - Expected success signal: focused permission-group page and page-hook suites pass in a single
    non-watch Jest run

## Test Cases

### T1: Permission group page and page-hook regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js src/pages/PermissionGroupManagement.test.js`
- Expected: page component extraction preserves toolbar actions, disabled state handling, and
  pending-delete confirmation behavior without changing current page wiring

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend permission group management | page decomposition preserves page-hook wiring and toolbar/delete interactions | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

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
  - page/page-hook behavior stays stable under the existing tests
- Fail when:
  - the command fails
  - page extraction breaks the `usePermissionGroupManagementPage` integration or toolbar and delete
    confirmation behavior

## Regression Scope

- `fronted/src/pages/PermissionGroupManagement.js`
- new component/helper module(s) under `fronted/src/features/permissionGroups/management/`
- `fronted/src/features/permissionGroups/management/usePermissionGroupManagementPage.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
