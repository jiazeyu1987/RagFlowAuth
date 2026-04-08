# Permission Group Management Page Refactor PRD

- Task ID: `tranche-fronted-src-pages-permissiongroupmanagem-20260408T082611`
- Created: `2026-04-08T08:26:11`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/pages/PermissionGroupManagement.js锛屾媶鍒嗗伐鍏锋爮銆佹枃浠跺す鏍戜晶杈广€佺姸鎬佷笌鍒犻櫎纭鍖哄煙銆佺紪杈戝櫒闈㈡澘绛夐〉闈㈠尯鍧楋紝淇濇寔 usePermissionGroupManagementPage 濂戠害涓庣幇鏈?Jest 娴嬭瘯琛屼负绋冲畾`

## Goal

Decompose `PermissionGroupManagement.js` so the toolbar, folder-tree sidebar, status and delete
confirmation area, and editor panel stop living in one 397-line route page, while preserving the
existing `usePermissionGroupManagementPage` contract and current folder and group management
behavior.

## Scope

- `fronted/src/pages/PermissionGroupManagement.js`
- new bounded component/helper module(s) under `fronted/src/features/permissionGroups/management/`
- focused frontend tests:
  - `fronted/src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js`
  - `fronted/src/pages/PermissionGroupManagement.test.js`
- task artifacts under
  `docs/tasks/tranche-fronted-src-pages-permissiongroupmanagem-20260408T082611/`

## Non-Goals

- changing permission group API payloads, drag-and-drop semantics, or folder/group business rules
- refactoring `usePermissionGroupManagement.js` in this tranche
- redesigning folder tree, group editor form, or page copy
- touching unrelated permission, user, or knowledge pages

## Preconditions

- `fronted/` can run focused Jest tests with `npm test`
- `usePermissionGroupManagementPage` remains the stable page-facing state and action contract
- existing permission-group page and page-hook Jest suites remain the source of truth for current
  behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- toolbar actions and icon-button rendering
- folder-tree sidebar layout and search input area
- error/hint and delete-confirmation rendering
- editor panel header and form container
- page and page-hook Jest coverage for permission-group management

## Phase Plan

### P1: Split the permission group page into focused render components

- Objective: Move major page render sections into bounded feature components while keeping
  `PermissionGroupManagement.js` as the composition page and preserving
  `usePermissionGroupManagementPage` as the page-state owner.
- Owned paths:
  - `fronted/src/pages/PermissionGroupManagement.js`
  - new component/helper module(s) under `fronted/src/features/permissionGroups/management/`
  - focused Jest tests listed above as needed
- Dependencies:
  - existing `usePermissionGroupManagementPage` contract
  - current toolbar actions, folder tree, and editor form integrations
- Deliverables:
  - slimmer page composition layer
  - extracted page render components for the main layout regions
  - unchanged folder/group management interactions

### P2: Focused frontend regression validation and task evidence

- Objective: Prove the bounded page refactor preserved current permission-group page behavior.
- Owned paths:
  - focused tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - focused frontend regression coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `PermissionGroupManagement.js` no longer directly owns the toolbar, sidebar wrapper,
  status/delete-confirmation block, and editor panel markup in one file.
- P1-AC2: the page continues to consume the same `usePermissionGroupManagementPage` state/action
  contract without page-level behavior changes.
- P1-AC3: toolbar actions, pending-delete confirmation, and editor rendering continue surfacing the
  existing states instead of introducing fallback paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused permission-group page Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `PermissionGroupManagement.js` remains the stable route page consuming
  `usePermissionGroupManagementPage`.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the `usePermissionGroupManagementPage`
  contract or permission-group feature API expectations
- page extraction would require fallback behavior for missing folder state, selection state, or
  delete-confirmation flow
