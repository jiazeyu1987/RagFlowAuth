# Route Navigation Refactor PRD

- Task ID: `continue-system-refactor-with-route-navigation-p-20260408T034152`
- Created: `2026-04-08T03:41:52`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Continue system refactor with route-navigation phase-1 frontend refactor while keeping behavior stable`

## Goal

Consolidate route metadata into one frontend route registry so that route paths, header titles,
navigation entries, and route guard metadata stop diverging between `App.js` and `Layout.js`,
while preserving current behavior.

## Scope

- `fronted/src/App.js`
- `fronted/src/components/Layout.js`
- new route-registry module(s) under `fronted/src/routes/`
- focused route/navigation tests
- `docs/exec-plans/active/route-navigation-refactor-phase-1.md`

## Non-Goals

- document-browser or preview refactors
- permission-model redesign
- backend changes
- cosmetic layout rewrites
- route path changes or new pages

## Preconditions

- Existing page components continue to be importable by lazy route definitions.
- Jest can run focused frontend route/layout tests.
- Navigation behavior in `Layout.js` is the baseline to preserve.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- page route definitions and route guards in `fronted/src/App.js`
- nav rendering and title resolution in `fronted/src/components/Layout.js`
- route aliases such as `/messages` -> inbox title behavior
- tool sub-route title overrides

## Phase Plan

### P1: Shared route registry

- Objective: Create one route registry that owns path, title, icon, nav inclusion, and guard metadata.
- Owned paths:
  - `fronted/src/routes/*`
  - `fronted/src/App.js`
  - `fronted/src/components/Layout.js`
- Dependencies:
  - existing page components
  - existing PermissionGuard behavior
- Deliverables:
  - shared route config module
  - App route rendering driven by registry
  - Layout nav/title rendering driven by registry

### P2: Focused regression coverage

- Objective: Prove that route metadata and nav visibility behavior stay stable after consolidation.
- Owned paths:
  - `fronted/src/components/Layout.test.js`
  - `fronted/src/routes/routeRegistry.test.js`
  - related task artifacts
- Dependencies:
  - P1 completed
- Deliverables:
  - focused tests for nav visibility and route title/alias metadata
  - task evidence for the frontend-only tranche

## Phase Acceptance Criteria

### P1

- P1-AC1: `App.js` no longer hardcodes the bulk of protected page route declarations inline; it renders them from shared route metadata.
- P1-AC2: `Layout.js` no longer owns a separate route/title/nav definition table for the same pages.
- P1-AC3: route metadata explicitly preserves special nav behavior such as admin-hidden entries, tool sub-route titles, and inbox aliases.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused frontend route/layout tests pass against the final code state.
- P2-AC2: task artifacts record the commands run and the remaining risk for the bounded route-navigation refactor.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- No route path or guard behavior changed unintentionally during consolidation.

## Blocking Conditions

- the shared route registry would require changing public route paths
- focused frontend validation cannot run
- preserving existing nav/alias behavior would require fallback logic instead of explicit metadata
