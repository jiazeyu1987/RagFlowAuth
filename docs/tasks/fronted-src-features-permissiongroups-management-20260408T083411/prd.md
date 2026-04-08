# Permission Group Management Hook Refactor PRD

- Task ID: `fronted-src-features-permissiongroups-management-20260408T083411`
- Created: `2026-04-08T08:34:11`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/features/permissionGroups/management/usePermissionGroupManagement.js，拆分初始化加载、目录/权限组选择与模式切换、权限组与文件夹变更动作、拖拽移动等共享逻辑，保持 usePermissionGroupManagementPage 和现有 Jest 行为稳定`

## Goal

Decompose `usePermissionGroupManagement.js` so the hook no longer owns initial data loading,
derived view data, CRUD orchestration, and drag-and-drop state transitions in one 500+ line file,
while preserving the external contract consumed by `usePermissionGroupManagementPage` and the
existing permission-group management UI.

## Scope

- `fronted/src/features/permissionGroups/management/usePermissionGroupManagement.js`
- new local helper module(s) or child hook(s) under
  `fronted/src/features/permissionGroups/management/`
- focused frontend tests:
  - `fronted/src/features/permissionGroups/management/usePermissionGroupManagement.test.js`
  - `fronted/src/features/permissionGroups/management/usePermissionGroupManagementPage.test.js`
  - `fronted/src/pages/PermissionGroupManagement.test.js`
- task artifacts under
  `docs/tasks/fronted-src-features-permissiongroups-management-20260408T083411/`

## Non-Goals

- changing permission-group backend payloads, API endpoints, or folder binding semantics
- changing `usePermissionGroupManagementPage.js` or page/component behavior beyond what is required
  to keep tests green
- redesigning folder tree, group editor form, or permission-group page layout
- introducing fallback behavior, mock data, or compatibility branches that are not already part of
  the feature

## Preconditions

- `fronted/` can run focused Jest tests through `npm test`
- `permissionGroupsApi` keeps the current methods used by the hook: list, listGroupFolders,
  listKnowledgeTree, listChats, create, update, remove, createFolder, updateFolder, removeFolder
- the current `usePermissionGroupManagementPage` return shape remains the stable consumer contract
- existing Jest suites remain the source of truth for current permission-group page behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- permission-group data bootstrapping and initial selection flow
- folder path, content rows, dataset items, and knowledge tree derived state
- group create, edit, delete, and folder CRUD flows
- drag-and-drop move handling for groups and folder hover/drop state
- page-hook and page-level Jest coverage consuming the hook contract

## Phase Plan

### P1: Split the hook into bounded loading, derived-state, and action helpers

- Objective: Move the densest responsibilities out of `usePermissionGroupManagement.js` without
  changing the page-facing hook contract.
- Owned paths:
  - `fronted/src/features/permissionGroups/management/usePermissionGroupManagement.js`
  - new helper module(s) or child hook(s) under
    `fronted/src/features/permissionGroups/management/`
- Dependencies:
  - existing `permissionGroupsApi` methods
  - `constants.js` and `utils.js`
  - current `usePermissionGroupManagementPage` consumer expectations
- Deliverables:
  - slimmer composition hook
  - isolated loading or action helpers for local responsibilities
  - preserved external return keys and current behavior

### P2: Focused regression validation and tranche evidence

- Objective: Prove the hook refactor preserves current permission-group management behavior and
  record reviewable evidence.
- Owned paths:
  - focused Jest tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - passing focused Jest suites
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `usePermissionGroupManagement.js` becomes a composition-oriented hook instead of directly
  embedding initialization, derived-state building, CRUD actions, and drag/drop orchestration in
  one file.
- P1-AC2: pure or bounded local helpers own repeated mapping, filtering, and action coordination so
  future permission-group changes no longer require editing multiple unrelated sections of the main
  hook.
- P1-AC3: `usePermissionGroupManagementPage` and page-level consumers continue using the same
  return contract and do not require fallback branches or behavior changes.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused permission-group Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, changed paths, verified acceptance ids, and
  any bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids are backed by evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `usePermissionGroupManagementPage.js` continues consuming `usePermissionGroupManagement()` without
  contract drift.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the public return shape of
  `usePermissionGroupManagement()`
- the hook cannot be decomposed without introducing fallback paths for missing folder, group, or
  drag state
