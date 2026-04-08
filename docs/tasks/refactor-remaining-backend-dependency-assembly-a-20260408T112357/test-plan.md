# Test Plan

- Task ID: `refactor-remaining-backend-dependency-assembly-a-20260408T112357`
- Created: `2026-04-08T11:23:57`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Refactor remaining backend dependency assembly and permission resolver hotspots without introducing fallback behavior`

## Test Scope

Validate that the refactor preserves:

- FastAPI dependency bootstrap and tenant dependency resolution
- permission resolution and `/api/auth/me` capability payload behavior
- user credential-history, lockout, and permission-group persistence behavior
- frontend layout shell behavior and nav rendering
- final integrated backend/frontend behavior for the refactored seams

Out of scope:

- broad end-to-end validation of every product workflow
- Playwright browser coverage for unrelated frontend screens
- deployment or environment rollout validation

## Environment

- Backend validation runs from the workspace root with `python -m pytest ...`
- Frontend validation runs from `D:\ProjectPackage\RagflowAuth\fronted`
- `fronted/node_modules` must already exist
- The current dirty working tree is intentional and must not be reset
- No fallback data or mock success paths may be introduced to satisfy the tests

## Accounts and Fixtures

- Backend tests use the repository's existing unit/integration fixtures and temporary databases
- Frontend tests use the repository's existing Jest fixtures and mocks
- No external credentials or production services are required for this task

If any required item is missing, the tester must fail fast and record the missing prerequisite.

## Commands

- `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_main_router_registration_unit.py backend/tests/test_tenant_db_isolation_unit.py`
  Expected success signal: dependency bootstrap and tenant-scoped dependency tests pass
- `python -m pytest backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_permissions_none_defaults.py backend/tests/test_auth_request_token_fail_fast_unit.py`
  Expected success signal: permission resolution and auth payload tests pass
- `python -m pytest backend/tests/test_auth_me_admin.py backend/tests/test_operation_approval_service_unit.py backend/tests/test_knowledge_management_manager_unit.py`
  Expected success signal: adjacent dependency/permission callers still pass
- `python -m pytest backend/tests/test_users_service_unit.py backend/tests/test_users_repo_unit.py backend/tests/test_users_router_unit.py backend/tests/test_password_security_unit.py backend/tests/test_auth_password_security_api.py backend/tests/test_user_store_username_refs_unit.py`
  Expected success signal: user-store callers, password history/lockout flows, and legacy password upgrade paths still pass after the store split
- `cd fronted; CI=true npm test -- --runInBand --runTestsByPath src/components/Layout.test.js src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/routes/routeRegistry.test.js`
  Expected success signal: layout shell and nav/auth tests pass once and exit cleanly

## Test Cases

### T1: Dependency bootstrap regression

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: integration
- Command: `python -m pytest backend/tests/test_dependencies_unit.py backend/tests/test_main_router_registration_unit.py backend/tests/test_tenant_db_isolation_unit.py`
- Expected: dependency bootstrap, router registration, and tenant-scoped dependency behavior pass after the decomposition

### T2: Permission resolver and auth payload regression

- Covers: P2-AC1, P2-AC2, P2-AC3
- Level: integration
- Command: `python -m pytest backend/tests/test_permission_resolver_sub_admin_management_unit.py backend/tests/test_auth_me_service_unit.py backend/tests/test_permissions_none_defaults.py backend/tests/test_auth_request_token_fail_fast_unit.py`
- Expected: permission policies, legacy defaults, and `/api/auth/me` payload semantics remain correct

### T3: Adjacent backend caller regression

- Covers: P1-AC2, P2-AC3
- Level: integration
- Command: `python -m pytest backend/tests/test_auth_me_admin.py backend/tests/test_operation_approval_service_unit.py backend/tests/test_knowledge_management_manager_unit.py`
- Expected: downstream dependency and permission consumers still pass

### T4: UserStore decomposition regression

- Covers: P3-AC1, P3-AC2, P3-AC3, P5-AC1
- Level: integration
- Command: `python -m pytest backend/tests/test_users_service_unit.py backend/tests/test_users_repo_unit.py backend/tests/test_users_router_unit.py backend/tests/test_password_security_unit.py backend/tests/test_auth_password_security_api.py backend/tests/test_user_store_username_refs_unit.py`
- Expected: user CRUD, credential policy, password-history/lockout behavior, legacy hash upgrade, and permission-group persistence stay stable after the split

### T5: Frontend layout shell regression

- Covers: P4-AC1, P4-AC2, P4-AC3
- Level: unit
- Command: `cd fronted; CI=true npm test -- --runInBand --runTestsByPath src/components/Layout.test.js src/hooks/useAuth.test.js src/components/PermissionGuard.test.js src/routes/routeRegistry.test.js`
- Expected: decomposed layout shell still renders titles, nav visibility, unread state, and auth-guard behavior correctly

### T6: Final focused regression closure

- Covers: P5-AC2, P5-AC3
- Level: mixed
- Command: rerun the relevant subset of T1 through T5 after final integration
- Expected: final backend/frontend focused regression commands still pass against the integrated code state

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | dependency assembly | validate bootstrap and tenant resolution seams | integration | P1-AC1, P1-AC2, P1-AC3 | `test-report.md#T1` |
| T2 | permission resolver | validate policy segmentation and auth payload contract | integration | P2-AC1, P2-AC2, P2-AC3 | `test-report.md#T2` |
| T3 | backend callers | validate adjacent dependency/permission consumers | integration | P1-AC2, P2-AC3 | `test-report.md#T3` |
| T4 | user store | validate store decomposition and legacy compatibility boundary | integration | P3-AC1, P3-AC2, P3-AC3, P5-AC1 | `test-report.md#T4` |
| T5 | frontend layout shell | validate shell decomposition and nav/auth behavior | unit | P4-AC1, P4-AC2, P4-AC3 | `test-report.md#T5` |
| T6 | final closure | validate final focused backend/frontend regression after integration | mixed | P5-AC2, P5-AC3 | `test-report.md#T6` |

## Evaluator Independence

- Mode: full-context
- Validation surface: real-runtime
- Required tools: python, pytest, npm
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run against the real repo and local runtime state without adding fallback behavior or mock success paths
- Escalation rule: do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis

## Pass / Fail Criteria

- Pass when:
  - all executed T1 through T6 cases pass
  - every PRD acceptance id is verified by at least one passing case
  - no fallback branches or silent downgrade paths are added to satisfy the refactor
- Fail when:
  - any targeted backend or frontend regression command fails
  - a required prerequisite is missing and not recorded
  - the refactor changes behavior in a way that breaks existing dependency, permission, user, or layout contracts

## Regression Scope

- FastAPI startup/lifespan dependency wiring
- tenant dependency resolution through `backend/app/core/auth.py`
- `/api/auth/me` payload and permission capability consumers
- user-management credential and permission-group operations
- frontend layout shell unread/nav/auth rendering behavior

## Reporting Notes

Write results to `test-report.md`.

Record exact commands, pass/fail outcome, and concise notes for each test case.
