# Execution Log

- Task ID: `address-remaining-refactor-hotspots-across-backe-20260408T093242`
- Created: `2026-04-08T09:32:42`

## Phase Entries

Append one reviewed section per executor pass using real phase ids and real evidence refs.

### Phase P1 - Backend dependency assembly decomposition

- Acceptance ids covered: `P1-AC1`, `P1-AC2`, `P1-AC3`
- Changed paths:
  - `backend/app/dependencies.py`
  - `backend/app/main.py`
  - `backend/tests/test_dependencies_unit.py`
- Implementation summary:
  - Extracted dependency DB path resolution and schema initialization into bounded helpers.
  - Introduced an internal dependency builder so shared runtime assembly, app dependency packaging, and operation-approval attachment are no longer interleaved in one long `create_dependencies()` routine.
  - Added `initialize_application_dependencies(app)` so FastAPI startup now uses one explicit application-state initialization path for global deps and tenant resolver wiring.
  - Added focused unit coverage for application-state initialization plus tenant dependency cache reuse and control-plane ownership.
- Validation run:
  - `python -m py_compile backend/app/dependencies.py backend/app/main.py backend/tests/test_dependencies_unit.py`
  - `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_tenant_db_isolation_unit.py backend/tests/test_main_router_registration_unit.py`
- Result:
  - Passing: `10 passed`
- Remaining risk / notes:
  - A broader unrelated check of `backend/tests/test_sub_admin_user_visibility_global_store_unit.py` currently returns `company_not_found` from the user-management path, which appears tied to concurrent users-module changes rather than the dependency-assembly seam owned by P1.

### Phase P2 - Permission/auth pipeline hardening and convergence

- Acceptance ids covered: `P2-AC1`, `P2-AC2`, `P2-AC3`
- Changed paths:
  - `backend/app/core/auth.py`
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
  - `backend/tests/test_auth_request_token_fail_fast_unit.py`
  - `backend/tests/test_auth_me_service_unit.py`
  - `backend/tests/test_permission_resolver_sub_admin_management_unit.py`
- Implementation summary:
  - Split permission resolution into staged helpers for dataset-index loading, group accumulation, node expansion, sub-admin scope augmentation, and snapshot assembly.
  - Split `/api/auth/me` payload building into narrower steps for permission-group projection, managed-root resolution, access-summary construction, and debug logging.
  - Replaced broad access-token verifier swallowing in `backend/app/core/auth.py` with `AuthXException`-scoped handling so invalid tokens still map to `401` while unexpected verifier/runtime failures now surface.
  - Removed broad catch-all swallowing from the core permission and auth-me path where it could hide broken authorization inputs or management-scope failures.
- Validation run:
  - `python -m py_compile backend/app/core/auth.py backend/app/core/permission_resolver.py backend/services/auth_me_service.py backend/tests/test_auth_request_token_fail_fast_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py`
  - `python -m pytest backend/tests/test_auth_request_token_fail_fast_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_auth_me_admin.py backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_permissions_none_defaults.py backend/tests/test_authz_authenticated_user_unit.py`
  - `CI=true npm test -- --runInBand --runTestsByPath src/hooks/useAuth.test.js src/components/PermissionGuard.test.js` (run from `fronted/`)
- Result:
  - Passing backend: `14 passed`
  - Passing frontend: `9 passed`
- Remaining risk / notes:
  - React Router future-flag warnings still appear in the `PermissionGuard` Jest run, but they do not change the current authorization assertions and were not expanded in this phase.

### Phase P3 - Data-security router boundary cleanup

- Acceptance ids covered: `P3-AC1`, `P3-AC2`, `P3-AC3`
- Changed paths:
  - `backend/app/modules/data_security/router.py`
  - `backend/app/modules/data_security/support.py`
  - `backend/tests/test_data_security_router_unit.py`
  - `backend/tests/test_data_security_router_stats.py`
- Implementation summary:
  - Moved data-security route helpers for settings shaping, backup preflight checks, restore-drill request parsing, audit log assembly, and package-hash hydration into a dedicated support module.
  - Reduced the router to HTTP-boundary work: auth/training checks, request-to-service orchestration, and HTTP exception mapping.
  - Centralized repeated backup run conflict status mapping and repeated data-security audit event logging so backup/run-full/cancel/restore-drill/list flows no longer hand-build the same audit envelope in each route.
- Validation run:
  - `python -m py_compile backend/app/modules/data_security/support.py backend/app/modules/data_security/router.py backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_router_stats.py`
  - `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_router_stats.py backend/tests/test_data_security_runner_stale_lock.py backend/tests/test_backup_restore_audit_unit.py backend/tests/test_training_compliance_api_unit.py`
- Result:
  - Passing backend: `22 passed`
- Remaining risk / notes:
  - `_backup_pack_stats()` and `_hydrate_job_package_hash()` still keep best-effort behavior for optional filesystem stats/hash backfill paths; this phase limited fail-fast tightening to request validation and route-orchestrated operations rather than passive diagnostics.

### Phase P4 - Frontend access-control and navigation convergence

- Acceptance ids covered: `P4-AC1`, `P4-AC2`, `P4-AC3`
- Changed paths:
  - `fronted/src/shared/auth/capabilities.js`
  - `fronted/src/hooks/useAuth.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/App.js`
  - `fronted/src/hooks/useAuth.test.js`
  - `fronted/src/components/PermissionGuard.test.js`
  - `fronted/src/routes/routeRegistry.test.js`
  - `fronted/src/components/Layout.test.js`
  - `fronted/e2e/tests/rbac.navigation-route-convergence.spec.js`
- Implementation summary:
  - Moved capability normalization and shared authorization evaluation into `fronted/src/shared/auth/capabilities.js`, including support for route/nav checks that pass when any one permission match is present.
  - Updated `useAuth`, `PermissionGuard`, `App`, `Layout`, and shared route metadata so route guarding and nav visibility now flow through the same route-level guard contract instead of `Layout`-only document-history special cases.
  - Added a focused Playwright regression covering document-history visibility/route access and the sub-admin data-security nav-vs-route split so the convergence is exercised in a real browser, not only in unit tests.
- Validation run:
  - `CI=true npm test -- --runInBand --runTestsByPath src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/components/Layout.test.js src/routes/routeRegistry.test.js` (run from `fronted/`)
  - `npx playwright test e2e/tests/rbac.navigation-route-convergence.spec.js --project=chromium --workers=1` (run from `fronted/`)
- Result:
  - Passing frontend: `20 passed`
  - Passing browser: `3 passed`
- Remaining risk / notes:
  - The seeded E2E viewer account currently has broader document-history access than the least-privilege case covered by this refactor, so the denied-path browser check now explicitly stubs a no-capability `/api/auth/me` response to keep the regression deterministic.
  - React Router future-flag warnings still appear during Jest runs but did not change the access-control assertions.

### Phase P5 - Selected page-controller hotspot decomposition

- Acceptance ids covered: `P5-AC1`, `P5-AC2`, `P5-AC3`
- Changed paths:
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js`
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePrefill.js`
  - `fronted/src/features/chat/hooks/useChatStream.js`
  - `fronted/src/features/chat/hooks/useChatStreamSupport.js`
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePage.test.js`
  - `fronted/src/features/chat/hooks/useChatStream.test.js`
  - `fronted/src/features/chat/hooks/useChatStreamSupport.test.js`
- Implementation summary:
  - Wired query-param prefill into the dedicated `useTrainingCompliancePrefill` hook so `useTrainingCompliancePage` no longer owns its prefill state machine inline alongside data loading and mutation submission.
  - Extracted stream-frame parsing, incremental assistant-message merge rules, empty-stream refresh gating, and failed-send rollback behavior into `useChatStreamSupport.js`, leaving `sendMessage()` responsible for request lifecycle orchestration instead of carrying the full SSE parser and merge heuristics inline.
  - Added focused helper coverage for chat-stream merge/rollback decisions while preserving the existing hook-level training-compliance and chat-stream tests against the refactored seams.
- Validation run:
  - `CI=true npm test -- --runInBand --runTestsByPath src/features/trainingCompliance/useTrainingCompliancePage.test.js src/features/chat/hooks/useChatStream.test.js src/features/chat/hooks/useChatStreamSupport.test.js` (run from `fronted/`)
- Result:
  - Passing frontend: `10 passed`
- Remaining risk / notes:
  - `useChatStream` intentionally still keeps its non-blocking first-turn rename call and post-stream session refresh hook, but those behaviors now sit behind narrower helper seams instead of sharing one large parser routine.

### Phase P6 - Focused regression, browser validation, and artifact closure

- Acceptance ids covered: `P6-AC1`, `P6-AC2`, `P6-AC3`
- Changed paths:
  - `docs/tasks/address-remaining-refactor-hotspots-across-backe-20260408T093242/execution-log.md`
  - `docs/tasks/address-remaining-refactor-hotspots-across-backe-20260408T093242/test-report.md`
- Implementation summary:
  - Re-ran the focused backend dependency/auth and data-security regressions against the final code state after the remaining frontend hotspot work landed.
  - Re-ran the focused frontend auth/navigation and hotspot-controller suites and then executed the Playwright access-control convergence spec to capture concrete browser evidence files under `output/playwright/`.
  - Performed a final mixed closure rerun over a smaller backend/frontend subset to confirm the integrated state still holds after all task artifacts and validation wiring were finished.
- Validation run:
  - `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_tenant_db_isolation_unit.py backend/tests/test_main_router_registration_unit.py backend/tests/test_auth_request_token_fail_fast_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_auth_me_admin.py backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_permissions_none_defaults.py backend/tests/test_authz_authenticated_user_unit.py`
  - `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_router_stats.py backend/tests/test_data_security_runner_stale_lock.py backend/tests/test_backup_restore_audit_unit.py backend/tests/test_training_compliance_api_unit.py`
  - `CI=true npm test -- --runInBand --runTestsByPath src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/components/Layout.test.js src/routes/routeRegistry.test.js` (run from `fronted/`)
  - `CI=true npm test -- --runInBand --runTestsByPath src/features/trainingCompliance/useTrainingCompliancePage.test.js src/features/chat/hooks/useChatStream.test.js src/features/chat/hooks/useChatStreamSupport.test.js` (run from `fronted/`)
  - `npx playwright test e2e/tests/rbac.navigation-route-convergence.spec.js --project=chromium --workers=1` (run from `fronted/`)
  - `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_data_security_router_unit.py`
  - `CI=true npm test -- --runInBand --runTestsByPath src/routes/routeRegistry.test.js src/features/trainingCompliance/useTrainingCompliancePage.test.js src/features/chat/hooks/useChatStream.test.js` (run from `fronted/`)
- Result:
  - Passing backend: `24 passed`, `22 passed`, `8 passed`
  - Passing frontend: `20 passed`, `10 passed`, `8 passed`
  - Passing browser: `3 passed`
- Remaining risk / notes:
  - Focused pytest runs still emit existing Pydantic deprecation and Requests dependency warnings, and focused Jest runs still emit React Router future-flag warnings; none changed the scoped refactor results for this task.

## Outstanding Blockers

- None yet.
