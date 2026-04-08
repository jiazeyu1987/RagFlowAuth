# Product Requirements Document

- Task ID: `address-remaining-refactor-hotspots-across-backe-20260408T093242`
- Created: `2026-04-08T09:32:42`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Address remaining refactor hotspots across backend dependencies, permission/auth flow, data security router boundaries, store responsibilities, frontend access-control convergence, and page-controller hotspots without introducing fallback behavior`

## Goal

Reduce the highest-cost refactor hotspots that still make this system hard to change safely, while preserving current behavior and fail-fast semantics. The outcome should leave backend dependency assembly, permission/auth flow, data-security routing boundaries, frontend access-control evaluation, and selected page-controller hotspots easier to trace, easier to test, and less prone to cross-module regressions.

## Scope

- Backend dependency assembly centered on `backend/app/dependencies.py` and its callers.
- Backend auth and permission flow centered on:
  - `backend/app/core/auth.py`
  - `backend/app/core/authz.py`
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
- Backend data-security API boundary centered on `backend/app/modules/data_security/router.py` and the supporting data-security service layer.
- Store-layer responsibility cleanup for the currently touched user and knowledge/document persistence seams where bounded extractions reduce mixed concerns without changing outward contracts.
- Frontend access-control convergence centered on:
  - `fronted/src/hooks/useAuth.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/routes/routeRegistry.js`
- Frontend hotspot controller decomposition centered on:
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js`
  - `fronted/src/features/chat/hooks/useChatStream.js`
  - `fronted/src/components/Layout.js`
- Focused backend, frontend, and real-browser validation plus task evidence.

## Non-Goals

- Full-system rewrite or architecture migration.
- Renaming real repository paths such as `fronted/` or `docs/maintance/`.
- Removing every legacy code path in this turn.
- Changing published API contracts, auth token formats, or permission semantics unless the existing implementation is internally duplicated and the outward behavior remains stable.
- Introducing fallback branches, mock behavior, compatibility shims, or silent downgrade paths.
- Cleaning unrelated dirty-worktree changes that predate this task.

## Preconditions

- The current working tree, including existing uncommitted refactor changes, is the source of truth for this task.
- Python is available and can run repository tests with `python -m pytest`.
- Frontend dependencies are installed under `fronted/node_modules`.
- Playwright is available from the frontend workspace for focused real-browser validation.
- If execution discovers direct conflicts with concurrent user edits in the same files, stop and record that conflict instead of overwriting or reverting those edits.
- If a required validation command or browser runtime is unavailable, stop and record the missing prerequisite in `task-state.json.blocking_prereqs`.

## Impacted Areas

- FastAPI application startup and lifespan wiring in `backend/app/main.py`.
- Dependency resolution and tenant-scoped dependency caching in `backend/app/dependencies.py` and `backend/app/core/auth.py`.
- Permission snapshot construction and `/api/auth/me` payload generation in `backend/app/core/permission_resolver.py`, `backend/app/core/authz.py`, and `backend/services/auth_me_service.py`.
- Data-security endpoints, scheduler/job orchestration, and audit logging in `backend/app/modules/data_security/router.py` and related services.
- User and knowledge/document persistence helpers in:
  - `backend/services/users/store.py`
  - `backend/services/users/manager.py`
  - `backend/services/kb/store.py`
- Frontend route metadata, nav visibility, route guarding, and auth normalization in:
  - `fronted/src/App.js`
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/hooks/useAuth.js`
- Frontend hotspot controllers and their tests in training-compliance and chat-stream feature folders.
- Existing focused backend and frontend test suites already covering permissions, auth-me payloads, data-security routes, layout, route registry, auth hooks, training compliance, and chat streaming.
- Prior tranche task artifacts under `docs/tasks/` that already completed related bounded refactors and now serve as historical context rather than active ownership.

## Phase Plan

### P1: Backend dependency assembly decomposition

- Objective: Break `backend/app/dependencies.py` into reviewable factory seams so global dependencies, tenant dependencies, and feature dependency groups stop being assembled in one large routine.
- Owned paths:
  - `backend/app/dependencies.py`
  - `backend/app/core/auth.py`
  - `backend/app/main.py`
  - any new bounded helper modules created under `backend/app/` or `backend/services/`
  - focused dependency tests under `backend/tests/`
- Dependencies:
  - Existing working-tree refactors must remain intact.
  - Tenant resolution behavior must stay stable.
- Deliverables:
  - Extracted dependency assembly helpers with stable fail-fast behavior.
  - Reduced direct complexity in `create_dependencies()` and tenant resolution paths.
  - Focused regression coverage for dependency creation and tenant-scoped lookup.

### P2: Permission/auth pipeline hardening and convergence

- Objective: Split permission resolution and auth-me payload generation into clearer stages, reduce broad catch-all exception swallowing on core authorization paths, and keep frontend/backend permission contracts aligned.
- Owned paths:
  - `backend/app/core/permission_resolver.py`
  - `backend/app/core/authz.py`
  - `backend/services/auth_me_service.py`
  - `backend/app/core/auth.py`
  - `fronted/src/hooks/useAuth.js`
  - `fronted/src/components/PermissionGuard.js`
  - shared auth helpers and matching tests
- Dependencies:
  - P1 may introduce helper modules used by auth resolution.
  - Existing capability contract from prior permission-model tranche remains the outward baseline.
- Deliverables:
  - Clearer staged permission/auth-me flow.
  - Fail-fast handling for core authorization logic where swallowing exceptions currently obscures breakage.
  - Focused backend and frontend regression coverage for auth and permission evaluation.

### P3: Data-security router boundary cleanup

- Objective: Thin the data-security router so HTTP concerns, prerequisite probing, business operations, and audit-record construction are no longer mixed in one router file.
- Owned paths:
  - `backend/app/modules/data_security/router.py`
  - `backend/app/modules/data_security/runner.py`
  - `backend/services/data_security/`
  - focused data-security tests under `backend/tests/`
- Dependencies:
  - P1/P2 must preserve dependency access and auth context behavior.
  - Existing data-security behavior and endpoint contracts stay stable.
- Deliverables:
  - Router delegates to extracted helpers/services for prerequisite checks and audit operations.
  - Focused tests cover preserved route behavior and failure conditions.

### P4: Frontend access-control and navigation convergence

- Objective: Eliminate remaining scattered route/nav access logic so route guarding and navigation visibility derive from one coherent metadata/evaluation path.
- Owned paths:
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/App.js`
  - `fronted/src/hooks/useAuth.js`
  - matching frontend tests
- Dependencies:
  - P2 keeps the auth/capability adapter stable.
  - Existing route metadata from the prior route-navigation tranche remains the starting point.
- Deliverables:
  - Navigation visibility logic extracted from `Layout` special cases where possible.
  - Shared route metadata and auth evaluation determine both route access and nav display.
  - Focused layout/route regression coverage plus real-browser confirmation.

### P5: Selected page-controller hotspot decomposition

- Objective: Reduce the highest-cost frontend controller hotspots by extracting bounded logic seams from `useTrainingCompliancePage`, `useChatStream`, and `Layout`.
- Owned paths:
  - `fronted/src/features/trainingCompliance/`
  - `fronted/src/features/chat/hooks/useChatStream.js`
  - `fronted/src/components/Layout.js`
  - new bounded helper or hook modules in those areas
  - matching frontend tests
- Dependencies:
  - P4 should already stabilize access-control and route behavior.
- Deliverables:
  - Training-compliance page logic split into smaller state/data/search or form helpers.
  - Chat streaming merge/parsing logic extracted into narrower helpers that are easier to test.
  - Layout polling/mobile/nav side effects split into narrower units where behavior stays stable.

### P6: Focused regression, browser validation, and artifact closure

- Objective: Validate the final refactor through focused backend/frontend commands and a real-browser smoke pass for the affected UI access-control paths, then close task evidence cleanly.
- Owned paths:
  - `docs/tasks/address-remaining-refactor-hotspots-across-backe-20260408T093242/`
  - any targeted test files updated for final validation
- Dependencies:
  - P1 through P5 completed and reviewable.
- Deliverables:
  - Execution evidence for each phase.
  - Independent-style test report with focused command results and browser evidence.
  - Successful completion check with all acceptance ids covered.

## Phase Acceptance Criteria

### P1

- P1-AC1: `backend/app/dependencies.py` no longer directly owns the full application object graph assembly in one large routine; feature-specific or stage-specific assembly has been extracted into bounded helpers/modules.
- P1-AC2: tenant-scoped dependency resolution still fails fast on invalid prerequisites and preserves current global-versus-tenant behavior without introducing fallback logic.
- P1-AC3: focused backend tests cover dependency creation and tenant-scoped resolution against the final code state.
- Evidence expectation: execution evidence references code changes plus passing focused dependency/auth tests.

### P2

- P2-AC1: backend permission resolution and `/api/auth/me` payload construction are split into clearer reviewable steps rather than one concentrated rule block with mixed expansion/output concerns.
- P2-AC2: core authorization and permission paths no longer hide important failures behind broad best-effort exception swallowing where that would obscure broken authorization behavior.
- P2-AC3: frontend auth evaluation and permission guards consume the shared capability contract without reintroducing divergent access-control rules.
- Evidence expectation: execution evidence references permission/auth code changes and passing focused backend/frontend auth tests.

### P3

- P3-AC1: `backend/app/modules/data_security/router.py` is reduced to HTTP boundary responsibilities, with prerequisite probing, audit payload construction, or core operation logic extracted to bounded helpers/services.
- P3-AC2: data-security routes preserve existing fail-fast request validation and do not introduce compatibility shims or silent downgrade paths.
- P3-AC3: focused backend data-security tests pass against the final code state.
- Evidence expectation: execution evidence references data-security boundary extraction and passing route-level tests.

### P4

- P4-AC1: route access and navigation visibility no longer rely on ad hoc `Layout`-only special cases such as standalone document-history visibility logic that is disconnected from shared route metadata.
- P4-AC2: shared route metadata plus shared auth evaluation now govern the affected nav and route-guard behavior consistently.
- P4-AC3: focused frontend tests and one real-browser validation pass confirm the affected navigation and access-control paths still work after convergence.
- Evidence expectation: execution evidence references route/layout changes, focused frontend test output, and browser evidence refs.

### P5

- P5-AC1: `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js` is decomposed into smaller bounded helpers/hooks so the page-level controller no longer directly owns all user-search, prefill, data loading, and form submission behavior in one file.
- P5-AC2: `fronted/src/features/chat/hooks/useChatStream.js` no longer keeps the full SSE parsing and merge heuristics embedded in one large `sendMessage()` routine without narrower helper seams.
- P5-AC3: focused frontend tests cover the decomposed training-compliance and chat-stream behavior against the final code state.
- Evidence expectation: execution evidence references controller decomposition plus passing targeted frontend tests.

### P6

- P6-AC1: focused backend regression commands for dependencies, auth/permissions, and data-security pass against the final code state.
- P6-AC2: focused frontend regression commands for auth, layout/routes, training-compliance, and chat-stream pass against the final code state.
- P6-AC3: `test-report.md` records a real-browser validation pass with concrete non-task-artifact evidence for the affected UI access-control surface.
- Evidence expectation: execution evidence references exact commands, browser artifacts, and final completion-script success.

## Done Definition

- All six phases are completed.
- Every acceptance id from P1 through P6 is marked completed with evidence.
- Backend dependency assembly is materially easier to review and reason about than the starting `create_dependencies()` shape.
- Core permission/auth logic is clearer, more fail-fast, and less concentrated.
- The data-security router is thinner and delegates non-HTTP concerns.
- Frontend route/nav access-control logic is more coherent and less special-cased.
- Training-compliance and chat-stream controller hotspots are decomposed into smaller reviewable units.
- Focused backend tests, focused frontend tests, and at least one real-browser validation path pass and are recorded in `test-report.md`.
- No fallback, mock, compatibility shim, or silent downgrade path is introduced.

## Blocking Conditions

- A direct conflict with concurrent user changes is discovered in the same owned files and cannot be reconciled safely.
- Required Python, frontend, or Playwright validation tooling is unavailable.
- Targeted tests expose a behavioral regression that cannot be fixed within the bounded phase scope.
- Repository drift makes the existing working tree inconsistent with the assumptions captured in this PRD.
- Any required refactor would force a public contract change, fallback branch, or silent downgrade not requested by the user.
