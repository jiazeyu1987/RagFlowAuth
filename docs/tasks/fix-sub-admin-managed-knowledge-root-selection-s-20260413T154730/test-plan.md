# Test Plan

- Task ID: `fix-sub-admin-managed-knowledge-root-selection-s-20260413T154730`
- Created: `2026-04-13T15:47:30`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Fix sub-admin managed knowledge root selection so a new or edited sub-admin cannot see or select directories already assigned to other active sub-admins; enforce the rule in both UI and backend; add automated tests.`

## Test Scope

Validate frontend filtering/disabled-node behavior, backend overlap rejection, and browser regressions for the real user-management managed-root flow. Broad unrelated user-management CRUD regressions are out of scope beyond the targeted checks listed below.

## Environment

- Backend unit tests from repository root using local Python.
- Frontend Jest tests from `fronted/`.
- Mocked Playwright regression run from `fronted/` with isolated ports `33003/38003`.
- Real doc E2E run from `fronted/` with `playwright.docs.config.js`.

## Accounts and Fixtures

- Local fake port fixtures in `backend/tests/test_users_manager_manager_user_unit.py`.
- Frontend mocked users/directories in the targeted Jest and Playwright tests.
- Doc E2E bootstrap users from `fronted/e2e/.auth/bootstrap-summary.json`.

## Commands

- `python -m pytest backend/tests/test_users_manager_manager_user_unit.py -q`
  Expected: all targeted backend manager tests pass.
- `npm test -- --runInBand --runTestsByPath src/features/users/utils/userManagedKbRoots.test.js src/features/users/components/KnowledgeRootNodeSelector.test.js src/features/users/hooks/useUserKnowledgeDirectories.test.js src/features/users/utils/userManagementMessages.test.js src/features/users/utils/userManagementState.test.js`
  Expected: targeted frontend unit suites pass.
- `npm test -- --runInBand --runTestsByPath src/features/users/hooks/useUserManagement.test.js src/features/users/components/modals/CreateUserModal.test.js src/features/users/utils/userManagementPageSections.test.js`
  Expected: page/hook plumbing suites pass.
- `npx playwright test e2e/tests/admin.users.managed-kb-root-visibility.spec.js --workers=1`
  Expected: mocked browser regression passes with the occupied root hidden or disabled.
- `npx playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js --workers=1`
  Expected: real doc user-management scenario passes after using an isolated managed root.
- `npx playwright test --config playwright.docs.config.js e2e/tests/docs.permission-groups.folder-visibility.spec.js --workers=1`
  Expected: real permission-group doc scenario remains green under the new backend rule.

## Test Cases

### T1: Frontend selection-state utility and selector rendering

- Covers: P1-AC1, P1-AC3
- Level: unit
- Command: Jest targeted paths for `userManagedKbRoots`, `KnowledgeRootNodeSelector`, and selector-state consumers.
- Expected: occupied roots are removed/disabled correctly, stale assignments do not poison the whole tree, and disabled container nodes remain expandable.

### T2: Backend overlap rejection

- Covers: P1-AC2, P1-AC3
- Level: unit
- Command: `python -m pytest backend/tests/test_users_manager_manager_user_unit.py -q`
- Expected: create/update attempts that overlap another active sub-admin root return `managed_kb_root_node_conflict` with `409`.

### T3: Browser regression for create-sub-admin modal

- Covers: P1-AC1, P1-AC3
- Level: e2e
- Command: `npx playwright test e2e/tests/admin.users.managed-kb-root-visibility.spec.js --workers=1`
- Expected: the create modal hides another sub-admin's occupied node, disables the shared ancestor container, and still allows selecting a free child.

### T4: Real doc user-management flow compatibility

- Covers: P1-AC4
- Level: doc-e2e
- Command: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js --workers=1`
- Expected: the real flow creates an extra sub-admin with an isolated managed root and passes end-to-end.

### T5: Real doc permission-group flow compatibility

- Covers: P1-AC4
- Level: doc-e2e
- Command: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.permission-groups.folder-visibility.spec.js --workers=1`
- Expected: the flow still validates read-only visibility without failing on the new backend managed-root conflict rule.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Frontend users selector | Occupied managed roots hidden/disabled correctly | unit | P1-AC1, P1-AC3 | `test-report.md` |
| T2 | Backend users manager | Overlapping roots rejected with conflict | unit | P1-AC2, P1-AC3 | `test-report.md` |
| T3 | Browser create flow | Create modal enforces occupied-root visibility rules | e2e | P1-AC1, P1-AC3 | `test-report.md` |
| T4 | Doc user management | Real sub-admin lifecycle remains green | doc-e2e | P1-AC4 | `test-report.md` |
| T5 | Doc permission groups | Real folder-visibility flow remains green | doc-e2e | P1-AC4 | `test-report.md` |

## Evaluator Independence

- Mode: full-context
- Validation surface: real-browser
- Required tools: pytest, react-scripts test, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Browser checks must use real Playwright sessions; backend and frontend checks must run against the checked-out repo.
- Escalation rule: fail fast if Playwright cannot boot or if the doc bootstrap environment is unavailable.

## Pass / Fail Criteria

- Pass when all listed commands succeed and the browser regression proves occupied managed roots are not selectable in the create flow.
- Fail when any targeted unit or browser command fails, or when a doc E2E still attempts to reuse an occupied managed root.

## Regression Scope

- User-management create modal
- User-management policy modal
- Backend sub-admin create/update flows
- Existing doc E2E flows that create secondary sub-admins

## Reporting Notes

Record exact commands, outcomes, and browser test names in `test-report.md`.
