# Permission Model Refactor Test Plan

- Task ID: `continue-system-refactor-with-permission-model-p-20260408T031346`
- Created: `2026-04-08T03:13:46`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Continue system refactor with permission-model phase-1 backend frontend local refactor while keeping behavior stable`

## Test Scope

Validate that the bounded permission-model refactor preserves behavior while moving permission
semantics to a single backend truth source plus one frontend adapter. The core areas are:

- `/api/auth/me` payload shape and capability semantics
- admin, viewer, scoped-tool, and sub-admin management permission cases
- `useAuth` login hydration and `can(...)` behavior
- `PermissionGuard` authorization behavior for roles plus capability checks
- navigation visibility paths that consume `useAuth`

Out of scope:

- real-browser route verification
- full route registry regression
- page-level flows that only mock `useAuth` and do not exercise auth normalization

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python runtime with `pytest`
- Frontend: Node.js/npm with Jest / react-scripts test
- No external credentials are required for the focused validation commands

## Accounts and Fixtures

- backend tests use local fakes and temporary SQLite fixtures already present in the repo
- frontend tests use mocked auth payloads and mocked `useAuth` consumers
- if backend or frontend test tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_auth_me_service_unit.py backend/tests/test_auth_me_admin.py backend/tests/test_permissions_none_defaults.py backend/tests/test_permission_resolver_tools_scope_unit.py backend/tests/test_permission_resolver_tool_guard_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py`
  - Expected success signal: all permission/auth-me tests pass and cover capability payload semantics
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/hooks/useAuth.test.js src/components/Layout.test.js src/components/PermissionGuard.test.js`
  - Expected success signal: auth normalization, layout navigation visibility, and guard behavior all pass

## Test Cases

### T1: Backend auth-me capability contract regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1
- Level: unit / integration
- Command: `python -m pytest backend/tests/test_auth_me_service_unit.py backend/tests/test_auth_me_admin.py backend/tests/test_permissions_none_defaults.py backend/tests/test_permission_resolver_tools_scope_unit.py backend/tests/test_permission_resolver_tool_guard_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py`
- Expected: auth-me payloads include the new capability contract and preserve the intended all/set/none semantics for admin, none, scoped, and sub-admin permission cases

### T2: Frontend auth capability adapter and guard regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC2, P3-AC3
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/hooks/useAuth.test.js src/components/Layout.test.js src/components/PermissionGuard.test.js`
- Expected: `useAuth` hydrates normalized capability data, `can(...)` delegates correctly, and `PermissionGuard`/`Layout` behavior remains stable

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend auth/permissions | auth-me capability payload and resolver semantics remain stable | unit/integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1 | `test-report.md#T1` |
| T2 | frontend auth/guards | capability adapter, `useAuth`, `PermissionGuard`, and layout consumers remain stable, with task evidence recorded for the bounded tranche | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC2, P3-AC3 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the exact commands against the real repo state without using fallback payloads or mock runtime shims beyond existing unit-test fixtures
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial verdict or discrepancy analysis is explicitly needed

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 both pass
  - auth-me keeps its existing fields and adds a valid capability contract
  - frontend auth code no longer re-encodes resource-specific policy branching in `useAuth.can(...)`
- Fail when:
  - any focused command fails
  - capability payload shape is invalid or requires silent fallback
  - route guard or tool/KB visibility behavior regresses in the focused consumer tests

## Regression Scope

- `backend/app/core/permission_resolver.py`
- `backend/services/auth_me_service.py`
- `backend/app/modules/auth/router.py`
- `fronted/src/hooks/useAuth.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/components/Layout.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether they passed or failed.
- If any prerequisite is missing, report it explicitly in `test-report.md` and `task-state.json.blocking_prereqs`.

The tester must remain independent from the executor and should prefer blind-first-pass unless a later discrepancy review is required.
