# Route Navigation Refactor Test Plan

- Task ID: `continue-system-refactor-with-route-navigation-p-20260408T034152`
- Created: `2026-04-08T03:41:52`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Continue system refactor with route-navigation phase-1 frontend refactor while keeping behavior stable`

## Test Scope

Validate that route metadata consolidation preserves:

- route path registration for protected pages
- header-title resolution
- nav visibility rules
- alias/title behavior for routes such as `/messages`

Out of scope:

- real-browser route verification
- document-browser behavior
- backend integration

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Frontend: Node.js/npm with Jest / react-scripts test

## Accounts and Fixtures

- tests use mocked `useAuth` and route metadata helpers
- if Jest tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/components/Layout.test.js src/components/PermissionGuard.test.js src/routes/routeRegistry.test.js`
  - Expected success signal: all focused route/navigation suites pass

## Test Cases

### T1: Route registry and layout navigation regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/components/Layout.test.js src/components/PermissionGuard.test.js src/routes/routeRegistry.test.js`
- Expected: route metadata drives layout navigation and titles without regressing current visibility or alias behavior

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend routes/navigation | shared route registry preserves nav visibility and title behavior | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run focused Jest suites against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial verdict

## Pass / Fail Criteria

- Pass when:
  - T1 passes
  - route/title/nav metadata is defined in one shared source
- Fail when:
  - focused Jest command fails
  - nav visibility or route alias behavior changes unexpectedly

## Regression Scope

- `fronted/src/App.js`
- `fronted/src/components/Layout.js`
- `fronted/src/routes/*`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
