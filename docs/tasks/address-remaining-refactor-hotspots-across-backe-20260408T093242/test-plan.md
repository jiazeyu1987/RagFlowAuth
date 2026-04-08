# Test Plan

- Task ID: `address-remaining-refactor-hotspots-across-backe-20260408T093242`
- Created: `2026-04-08T09:32:42`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Address remaining refactor hotspots across backend dependencies, permission/auth flow, data security router boundaries, store responsibilities, frontend access-control convergence, and page-controller hotspots without introducing fallback behavior`

## Test Scope

Validate that the bounded refactor preserves:

- backend dependency creation and tenant-scoped dependency lookup
- backend permission/auth payload behavior and fail-fast authorization semantics
- data-security route behavior and validation failures
- frontend route guarding, navigation visibility, and auth evaluation
- decomposed training-compliance and chat-stream controller behavior
- affected UI access-control/navigation paths in a real browser

Out of scope:

- broad end-to-end validation of every feature area in the product
- removing all legacy code paths
- deployment, packaging, or infra rollout verification

## Environment

- Workspace root: `D:\ProjectPackage\RagflowAuth`
- Backend validation runs from the workspace root with `python -m pytest ...`
- Frontend validation runs from `D:\ProjectPackage\RagflowAuth\fronted`
- Node dependencies must already exist in `fronted/node_modules`
- Real-browser validation uses Playwright from the frontend workspace
- Validation assumes the current dirty working tree is intentional and must not be reset or cleaned automatically

## Accounts and Fixtures

- Unit/integration tests rely on the repository's existing backend/frontend test fixtures
- Real-browser validation may use existing local app/test harness setup only; if that setup is missing, fail fast and record the missing prerequisite instead of simulating success
- No hidden credentials or external production services are assumed

## Commands

- `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_permissions_none_defaults.py`
  Expected success signal: all targeted backend dependency/auth tests pass
- `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_router_stats.py backend/tests/test_data_security_runner_stale_lock.py`
  Expected success signal: all targeted data-security tests pass
- `cd fronted; npm test -- --watch=false --runInBand src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/components/Layout.test.js src/routes/routeRegistry.test.js`
  Expected success signal: affected auth/layout/route tests pass once and exit cleanly
- `cd fronted; npm test -- --watch=false --runInBand src/features/trainingCompliance/useTrainingCompliancePage.test.js src/features/chat/hooks/useChatStream.test.js`
  Expected success signal: affected hotspot-controller tests pass once and exit cleanly
- `cd fronted; npx playwright test --grep @refactor-access-control --workers=1`
  Expected success signal: focused browser case passes and records a screenshot, trace, or equivalent evidence file

If the browser test does not yet exist, the executor must add a narrowly scoped one as part of the task instead of skipping real-browser validation.

## Test Cases

### T1: Backend dependency and auth regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: integration
- Command: `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_permissions_none_defaults.py`
- Expected: dependency creation, tenant scope lookup, auth-me payload, and permission defaults all pass with no fallback behavior introduced

### T2: Data-security route regression

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: integration
- Command: `python -m pytest backend/tests/test_data_security_router_unit.py backend/tests/test_data_security_router_stats.py backend/tests/test_data_security_runner_stale_lock.py`
- Expected: data-security route behavior, prerequisite handling, and stats paths pass against the refactored boundary

### T3: Frontend auth and navigation unit regression

- Covers: P2-AC3, P4-AC1, P4-AC2
- Level: unit
- Command: `cd fronted; npm test -- --watch=false --runInBand src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/components/Layout.test.js src/routes/routeRegistry.test.js`
- Expected: shared auth evaluation, guards, layout nav rendering, and route metadata behavior remain stable

### T4: Frontend hotspot-controller regression

- Covers: P5-AC1, P5-AC2, P5-AC3
- Level: unit
- Command: `cd fronted; npm test -- --watch=false --runInBand src/features/trainingCompliance/useTrainingCompliancePage.test.js src/features/chat/hooks/useChatStream.test.js`
- Expected: decomposed training-compliance and chat-stream behavior passes targeted regression coverage

### T5: Real-browser access-control smoke

- Covers: P4-AC3, P6-AC3
- Level: e2e
- Command: `cd fronted; npx playwright test --grep @refactor-access-control --workers=1`
- Expected: a focused navigation/access-control path passes in a real browser and produces at least one non-task-artifact evidence file

### T6: Final focused regression closure

- Covers: P6-AC1, P6-AC2
- Level: mixed
- Command: rerun the relevant subset of T1 through T4 after final integration
- Expected: final backend and frontend focused regression commands still pass against the integrated code state

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend dependencies and auth | validate decomposed dependency/auth pipeline | integration | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |
| T2 | data security | validate router boundary cleanup and route behavior | integration | P3-AC1, P3-AC2, P3-AC3 | `test-report.md#T2` |
| T3 | frontend auth/navigation | validate shared access-control and nav convergence | unit | P2-AC3, P4-AC1, P4-AC2 | `test-report.md#T3` |
| T4 | frontend hotspot controllers | validate decomposed training-compliance and chat-stream logic | unit | P5-AC1, P5-AC2, P5-AC3 | `test-report.md#T4` |
| T5 | browser validation | validate affected access-control/nav behavior in a real browser | e2e | P4-AC3, P6-AC3 | `test-report.md#T5` |
| T6 | final closure | validate final backend/frontend focused regression after integration | mixed | P6-AC1, P6-AC2 | `test-report.md#T6` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: python, pytest, npm, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run against the real repo and runtime; browser validation must use a real Playwright browser session and record concrete evidence
- Escalation rule: do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis

## Pass / Fail Criteria

- Pass when:
  - all executed T1 through T6 cases pass
  - every PRD acceptance id is verified by at least one passing case
  - the real-browser case records at least one screenshot, trace, video, HAR, or similar evidence file outside the task artifact directory
  - no required command is skipped without a recorded blocking prerequisite
- Fail when:
  - any targeted backend or frontend regression command fails
  - the browser case fails or lacks concrete evidence
  - a required prerequisite is missing and unrecorded
  - behavior changes require fallback or silent downgrade to keep tests green

## Regression Scope

- Backend startup and lifespan wiring touched by dependency extraction
- Tenant-scoped auth resolution and `/api/auth/me`
- Permission-group and sub-admin management behavior
- Data-security settings, backup jobs, cancel flow, and restore-drill routes
- Frontend route rendering, nav visibility, and permission guarding
- Training-compliance form/search/prefill flow
- Chat-stream SSE merge and message state update behavior

## Reporting Notes

Write results to `test-report.md`.

Record exact commands, pass/fail outcome, and evidence refs for each test case. For T5, include a non-task-artifact evidence path such as an image, trace, or report artifact produced during Playwright execution.
