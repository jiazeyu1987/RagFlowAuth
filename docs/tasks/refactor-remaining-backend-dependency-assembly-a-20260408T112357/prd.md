# PRD

- Task ID: `refactor-remaining-backend-dependency-assembly-a-20260408T112357`
- Created: `2026-04-08T11:23:57`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Refactor remaining backend dependency assembly and permission resolver hotspots without introducing fallback behavior`

## Goal

Reduce the remaining architectural hotspots called out in the code review so dependency assembly, permission resolution, user persistence logic, frontend shell state, and legacy-compatibility rules are easier to reason about and modify without reintroducing fallback behavior or hidden side effects.

## Scope

- `backend/app/dependencies.py`
- backend dependency bootstrap helpers introduced by this task
- `backend/app/core/permission_resolver.py`
- backend permission resolver helpers introduced by this task
- `backend/services/users/store.py`
- backend user-store helpers introduced by this task
- `backend/services/users/password.py`
- `fronted/src/components/Layout.js`
- frontend layout hooks/components introduced by this task
- focused backend and frontend regression tests that protect the refactored seams

## Non-Goals

- Rewriting unrelated backend service modules outside the dependency/permission/user-store scope
- Changing API contracts for `/api/auth/me`, route authorization, or existing user-management endpoints
- Removing tenant scoping, notification defaults, or operation-approval wiring behavior
- Removing legacy password compatibility if the repository still contains real legacy hashes that require support
- Visual redesign of the frontend shell

## Preconditions

- Python and pytest must be runnable from the workspace root
- Node and npm must be runnable from `fronted/`
- `fronted/node_modules` must already exist
- Existing backend/frontend tests for dependencies, auth, permissions, users, and layout must remain available
- Repository schema helpers and the local workspace must remain readable and writable

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- FastAPI startup and lifespan wiring in `backend/app/main.py`
- request-scoped dependency resolution in `backend/app/core/auth.py`
- auth payload building in `backend/services/auth_me_service.py`
- user-management callers that rely on `UserStore`
- permission-group and sub-admin management flows
- frontend route shell rendering through `fronted/src/components/Layout.js`
- focused tests under `backend/tests/` and `fronted/src/**/*.test.js`

## Phase Plan

### P1: Dependency assembly boundary decomposition

- Objective: split dependency graph construction into clearer bootstrap stages so global runtime setup, app dependency packaging, and tenant dependency resolution no longer live as one cross-module control point.
- Owned paths:
  - `backend/app/dependencies.py`
  - new backend dependency helper modules introduced for bootstrap/runtime grouping
  - `backend/tests/test_dependencies_unit.py`
- Dependencies:
  - existing app startup registration in `backend/app/main.py`
  - tenant resolution through `backend/app/core/auth.py`
- Deliverables:
  - explicit dependency bootstrap seams for global runtime setup, app dependency packaging, and tenant-scoped resolution
  - focused dependency tests for the new seams

### P2: Permission resolver segmentation and legacy-default isolation

- Objective: break permission resolution into bounded resource-specific stages and move legacy default semantics into explicit policy helpers instead of keeping them embedded in the main rule accumulator.
- Owned paths:
  - `backend/app/core/permission_resolver.py`
  - new backend permission helper/policy modules introduced by this task
  - `backend/services/auth_me_service.py`
  - `backend/tests/test_permission_resolver_sub_admin_management_unit.py`
  - `backend/tests/test_auth_me_service_unit.py`
  - `backend/tests/test_permissions_none_defaults.py`
- Dependencies:
  - permission-group data from `deps.permission_group_store`
  - management scope data from `knowledge_management_manager` and `chat_management_manager`
- Deliverables:
  - explicit permission policy/default helpers
  - segmented permission/resource resolution flow
  - preserved `/api/auth/me` payload semantics

### P3: UserStore responsibility split

- Objective: keep the `UserStore` public contract stable while moving credential history/lockout handling and permission-group membership persistence behind narrower internal stores or helpers.
- Owned paths:
  - `backend/services/users/store.py`
  - new backend user-store helper modules introduced by this task
  - `backend/services/users/password.py`
  - focused backend user/auth tests affected by the refactor
- Dependencies:
  - existing `UserStore` callers across auth, user management, and permission flows
- Deliverables:
  - a thinner `UserStore` coordinator
  - isolated credential-history/lockout and group-membership persistence logic
  - tests preserving existing user-management behavior

### P4: Frontend layout shell decomposition

- Objective: reduce `Layout` into a shell composition layer by extracting unread polling, responsive sidebar behavior, and nav rendering concerns into dedicated hooks/components.
- Owned paths:
  - `fronted/src/components/Layout.js`
  - new frontend layout hook/component files introduced by this task
  - `fronted/src/components/Layout.test.js`
- Dependencies:
  - `useAuth`
  - route metadata in `fronted/src/routes/routeRegistry.js`
  - inbox unread sync helpers
- Deliverables:
  - decomposed layout shell pieces with existing behavior preserved
  - focused layout regression coverage

### P5: Legacy compatibility isolation and focused closure

- Objective: isolate legacy password-hash handling and deprecated user group compatibility semantics to explicit, reviewable boundaries, then run focused backend/frontend regression closure.
- Owned paths:
  - `backend/services/users/password.py`
  - backend user/auth compatibility helpers introduced by this task
  - `docs/tasks/refactor-remaining-backend-dependency-assembly-a-20260408T112357/execution-log.md`
  - `docs/tasks/refactor-remaining-backend-dependency-assembly-a-20260408T112357/test-report.md`
- Dependencies:
  - completion of P1 through P4
- Deliverables:
  - explicit legacy compatibility boundaries instead of scattered conditionals
  - focused regression evidence covering all phases

## Phase Acceptance Criteria

### P1

- P1-AC1: `backend/app/dependencies.py` no longer directly owns the full lifecycle of schema preparation, runtime service construction, app dependency packaging, and tenant dependency cache resolution in one module-level control path.
- P1-AC2: global dependency bootstrap and tenant-scoped dependency resolution use explicit bounded helpers or modules, while preserving fail-fast startup behavior and current tenant/global semantics.
- P1-AC3: focused dependency tests cover the new bootstrap seams and tenant-scoped behavior against the final code state.
- Evidence expectation: `execution-log.md` records the dependency-boundary changes and passing focused dependency tests.

### P2

- P2-AC1: permission resolution is broken into narrower resource/policy stages instead of embedding KB, chat, tool, and sub-admin scope accumulation in one large rule path.
- P2-AC2: legacy permission defaults such as missing `can_view_tools` or `can_view_kb_config` behavior are centralized in explicit helpers/policies rather than being silently embedded in the accumulator logic.
- P2-AC3: `/api/auth/me` and existing permission consumers preserve the final capability/permission contract without reintroducing silent exception swallowing or menu/backend drift.
- Evidence expectation: `execution-log.md` records the permission-policy refactor and passing focused permission/auth payload tests.

### P3

- P3-AC1: `backend/services/users/store.py` no longer directly owns all credential-history, lockout-state, and permission-group relationship persistence logic inline with core user CRUD operations.
- P3-AC2: user credential and permission-group persistence behavior remains fail-fast and transactionally consistent after the split, without adding fallback branches.
- P3-AC3: focused backend tests cover the refactored user-store seams against the final code state.
- Evidence expectation: `execution-log.md` records the user-store split and passing focused backend user/auth regressions.

### P4

- P4-AC1: `fronted/src/components/Layout.js` is reduced to shell composition responsibilities, with responsive sidebar state, inbox polling, or nav rendering extracted into bounded hooks/components.
- P4-AC2: route metadata and shared auth evaluation still govern nav visibility after the split, with no new ad hoc shell-only access rules introduced.
- P4-AC3: focused frontend layout tests pass against the final decomposed shell state.
- Evidence expectation: `execution-log.md` records the layout decomposition and passing focused frontend layout regressions.

### P5

- P5-AC1: legacy password-hash verification and deprecated user-group compatibility semantics are isolated to explicit helpers or compatibility modules instead of being scattered across store and auth paths.
- P5-AC2: focused backend/frontend regression commands pass against the final integrated state for dependencies, permissions, user store, and layout.
- P5-AC3: task artifacts record final implementation evidence and test evidence for every acceptance id without requiring fallback behavior or undocumented prerequisites.
- Evidence expectation: `execution-log.md` and `test-report.md` record the legacy-boundary isolation plus final focused regression results.

## Done Definition

- All five phases are completed
- Every acceptance id is marked completed with evidence in `execution-log.md` or `test-report.md`
- Focused backend tests for dependencies, permissions, auth payloads, and user-store behavior pass
- Focused frontend tests for layout behavior pass
- Final completion check passes with no missing evidence

## Blocking Conditions

- Required pytest or npm tooling is missing or unusable
- Existing dependency/auth/user/layout tests needed for validation are unavailable and cannot be restored from the current repo state
- Legacy password compatibility cannot be safely isolated because the current repo or fixtures still require undocumented behavior that would be broken by the refactor
- Dependency bootstrap changes reveal tenant/global state assumptions that cannot be preserved without introducing fallback behavior
