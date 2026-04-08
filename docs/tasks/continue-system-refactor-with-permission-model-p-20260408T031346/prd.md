# Permission Model Refactor PRD

- Task ID: `continue-system-refactor-with-permission-model-p-20260408T031346`
- Created: `2026-04-08T03:13:46`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Continue system refactor with permission-model phase-1 backend frontend local refactor while keeping behavior stable`

## Goal

Make backend permission resolution the only policy truth source for the covered flows and
reduce frontend permission duplication to a single adapter layer, while keeping current
behavior stable for login hydration, route protection, tool visibility, KB visibility,
and existing `/api/auth/me` consumers.

## Scope

- `backend/app/core/permission_resolver.py`
- `backend/services/auth_me_service.py`
- `backend/app/modules/auth/router.py`
- backend tests covering resolver and `/api/auth/me`
- `fronted/src/hooks/useAuth.js`
- `fronted/src/components/PermissionGuard.js`
- new frontend auth capability helper(s) under `fronted/src/shared/auth/`
- focused frontend auth/layout/guard tests
- `docs/exec-plans/active/permission-model-refactor-phase-1.md`

## Non-Goals

- full route registry consolidation in `fronted/src/App.js`
- permission-group storage redesign
- changes to backend route paths or response envelopes
- broad rewrites of pages already consuming `useAuth`
- adding fallback paths for missing capability payloads
- unrelated cleanup in notification, approval, or data-security modules

## Preconditions

- Python test runtime is available for focused backend permission tests.
- Node.js/npm and Jest are available for focused frontend auth tests.
- `/api/auth/me` remains the canonical login-hydration endpoint.
- Existing permission snapshot semantics in `permission_resolver.py` remain the behavior baseline.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- `backend/app/core/authz.py` callers that depend on `PermissionSnapshot`
- `/api/auth/me` login hydration flow used by `fronted/src/features/auth/api.js`
- `fronted/src/components/Layout.js` navigation visibility that depends on `useAuth`
- routes guarded by `PermissionGuard`
- pages and tests mocking `useAuth.can`, `canViewTools`, `accessibleKbs`, or raw `permissions`

## Phase Plan

### P1: Backend capability contract

- Objective: Add a stable capability payload to `/api/auth/me` directly from backend
  permission resolution, without changing existing fields or route behavior.
- Owned paths:
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
  - backend permission/auth-me tests
- Dependencies:
  - existing `PermissionSnapshot`
  - existing `/api/auth/me` consumer contract
- Deliverables:
  - a normalized `capabilities` payload in auth-me responses
  - focused tests for admin, none, scoped-tool, and sub-admin management cases

### P2: Frontend auth normalization and guard convergence

- Objective: Replace inline frontend permission semantics with one shared capability adapter
  and keep `useAuth.can()` as a compatibility facade.
- Owned paths:
  - `fronted/src/shared/auth/*`
  - `fronted/src/hooks/useAuth.js`
  - `fronted/src/components/PermissionGuard.js`
  - focused frontend auth/layout/guard tests
- Dependencies:
  - P1 capability payload
  - existing `useAuth` consumer API
- Deliverables:
  - a validated capability adapter
  - `useAuth.can()` delegating to the adapter
  - `PermissionGuard` delegating to shared authorization logic

### P3: Regression validation and task closure

- Objective: Prove the refactor preserved behavior for route guarding and capability evaluation,
  then close the task artifacts with execution and test evidence.
- Owned paths:
  - `docs/tasks/continue-system-refactor-with-permission-model-p-20260408T031346/*`
  - `docs/exec-plans/active/permission-model-refactor-phase-1.md`
- Dependencies:
  - P1 and P2 completed
  - focused backend and frontend validation runnable
- Deliverables:
  - completed execution log
  - completed test report
  - task-state aligned with acceptance evidence

## Phase Acceptance Criteria

### P1

- P1-AC1: `/api/auth/me` responses include a stable `capabilities` object built from backend
  permission resolution and keep existing `permissions`, `accessible_kbs`,
  `accessible_kb_ids`, and `accessible_chats` fields unchanged.
- P1-AC2: capability output correctly preserves `ALL`, `SET`, and `NONE` semantics for scoped
  resources such as tools and knowledge-base visibility.
- P1-AC3: focused backend tests cover admin, no-access, scoped tools, and sub-admin management
  cases against the final auth-me payload / snapshot semantics.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `fronted/src/hooks/useAuth.js` no longer hardcodes resource-specific permission rules
  inside `can(...)`; it delegates to a shared capability evaluator.
- P2-AC2: `PermissionGuard` no longer reinterprets permission semantics independently; it uses
  shared auth authorization evaluation.
- P2-AC3: invalid or missing capability payloads fail fast during auth normalization instead of
  silently downgrading to inferred permissions.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused backend regression commands pass against the final code state.
- P3-AC2: focused frontend regression commands pass against the final code state.
- P3-AC3: task artifacts record which commands ran, what acceptance ids they verified, and any
  residual risk that remains after the bounded permission-model refactor.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- Every acceptance id has evidence in `execution-log.md` or `test-report.md`.
- `task-state.json` records `planner_review_status` as `approved`.
- `task-state.json` records all phases and acceptance ids as completed.
- `test_status` is `passed`.
- No fallback branch was added for missing capability data.

## Blocking Conditions

- `/api/auth/me` cannot be changed without breaking a required existing contract.
- backend or frontend focused validation cannot run in this environment.
- capability payload validation would require silent fallback to raw permission inference.
- the refactor reveals a broader contract break that requires route-registry or schema redesign
  beyond this bounded phase.
