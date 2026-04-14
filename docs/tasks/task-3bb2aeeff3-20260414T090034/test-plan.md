# Test Plan

- Task ID: `task-3bb2aeeff3-20260414T090034`
- Created: `2026-04-14T09:00:34`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Fix frontend garbled text, convert Chinese copy to English, and make wording more formal.`

## Test Scope

Validate only the scoped UI text work:
- removal of mojibake in targeted frontend files,
- conversion of targeted user-facing copy to formal English,
- preservation of existing runtime behavior.

Out of scope:
- full frontend localization replacement,
- non-scoped feature pages,
- backend/API behavior changes.

## Environment

- OS: Windows (PowerShell).
- Repo root: `D:\ProjectPackage\RagflowAuth`.
- Frontend root: `D:\ProjectPackage\RagflowAuth\fronted`.
- Node modules installed in `fronted`.
- Playwright browsers installed for the same environment.

## Accounts and Fixtures

- For unit tests: no external account required.
- For `docs.approval-config.spec.js`: doc admin E2E bootstrap/fixtures must be available.
- For `rbac.unauthorized.spec.js`: RBAC E2E fixture users must be available.

Fail-fast:
- If fixtures, runtime, or tools are missing, stop immediately and record the missing prerequisite and blocked cases.

## Commands

Run from repo root unless noted.

1. Static scoped check (mojibake guard)
```powershell
rg -n "鍔|璇|鏈|瀹|涓婃捣|鏃犳潈闄|閿欒|璁烘枃|涓撳埄|鍖呰|鑽洃" fronted/src/pages/Tools.js fronted/src/pages/UserManagement.js fronted/src/App.js fronted/src/components/PermissionGuard.js fronted/src/components/Layout.js fronted/src/components/layout/LayoutHeader.js fronted/src/components/layout/LayoutSidebar.js fronted/src/features/auth/useLoginPage.js fronted/src/shared/errors/userFacingErrorMessages.js fronted/src/pages/Unauthorized.js fronted/e2e/tests/docs.approval-config.spec.js
```
Expected success signal: no matches for known garbled fragments after implementation.

2. Scoped unit tests
```powershell
Set-Location fronted; npm test -- --watch=false --runInBand src/components/PermissionGuard.test.js src/features/auth/useLoginPage.test.js src/pages/LoginPage.test.js src/pages/Tools.test.js src/shared/errors/userFacingErrorMessages.test.js
```
Expected success signal: all listed test files pass.

3. Real-browser RBAC unauthorized check
```powershell
Set-Location fronted; npx playwright test e2e/tests/rbac.unauthorized.spec.js --workers=1
```
Expected success signal: spec passes and unauthorized page assertions remain valid.

4. Real-browser docs approval-config check
```powershell
Set-Location fronted; npx playwright test e2e/tests/docs.approval-config.spec.js --workers=1
```
Expected success signal: spec passes with corrected non-garbled test strings.

## Test Cases

### T1: Scoped mojibake removal
- Covers: P1-AC1
- Level: static
- Command: Command 1
- Expected: no known garbled fragments remain in scoped files.

### T2: Formal English copy in auth and guard flows
- Covers: P1-AC2, P2-AC1
- Level: unit
- Command: Command 2
- Expected: updated assertions confirm formal English strings for login/guard/error mapping.
- Expected: updated assertions confirm formal English strings for login/guard/error mapping and tools page content.

### T3: No behavior regression from text-only edits
- Covers: P1-AC3
- Level: unit
- Command: Command 2 plus diff inspection
- Expected: only string/test-label text changed; no logic/API contract updates.

### T4: Unauthorized route remains valid in real browser
- Covers: P2-AC2
- Level: e2e
- Command: Command 3
- Expected: `/unauthorized` route and title visibility checks pass.

### T5: Approval-config docs spec has no garbled literals
- Covers: P1-AC1, P2-AC2
- Level: e2e
- Command: Command 4
- Expected: spec title and assertion text are readable and test passes.

### T6: Change boundary enforcement
- Covers: P2-AC3
- Level: scm
- Command: `git diff --name-only -- fronted/src/App.js fronted/src/components/PermissionGuard.js fronted/src/components/Layout.js fronted/src/components/layout/LayoutHeader.js fronted/src/components/layout/LayoutSidebar.js fronted/src/features/auth/useLoginPage.js fronted/src/shared/errors/userFacingErrorMessages.js fronted/src/pages/Unauthorized.js fronted/src/pages/Tools.js fronted/src/pages/UserManagement.js fronted/src/components/PermissionGuard.test.js fronted/src/features/auth/useLoginPage.test.js fronted/src/pages/LoginPage.test.js fronted/src/pages/Tools.test.js fronted/src/shared/errors/userFacingErrorMessages.test.js fronted/e2e/tests/rbac.unauthorized.spec.js fronted/e2e/tests/docs.approval-config.spec.js docs/tasks/task-3bb2aeeff3-20260414T090034/prd.md docs/tasks/task-3bb2aeeff3-20260414T090034/test-plan.md docs/tasks/task-3bb2aeeff3-20260414T090034/execution-log.md docs/tasks/task-3bb2aeeff3-20260414T090034/test-report.md docs/tasks/task-3bb2aeeff3-20260414T090034/task-state.json`
- Expected: all task-introduced changes are contained within scoped source, linked tests, and task artifacts.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Shared copy files | Mojibake fragments removed | static | P1-AC1 | command output |
| T2 | Login/guard/error map | Formal English copy assertions | unit | P1-AC2, P2-AC1 | jest output |
| T3 | Scoped source files | Text-only change boundary | review+unit | P1-AC3 | diff + jest output |
| T4 | Unauthorized route | Real browser unauthorized page validation | e2e | P2-AC2 | Playwright report/artifacts |
| T5 | Docs approval config spec | Real browser run with corrected text literals | e2e | P1-AC1, P2-AC2 | Playwright report/artifacts |
| T6 | Task change boundary | No task-introduced out-of-scope edits | scm | P2-AC3 | scoped git diff output |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run listed unit and Playwright commands against this repo runtime.
- Escalation rule: do not inspect withheld artifacts before initial verdict.

## Pass / Fail Criteria

- Pass when:
  - All commands required for available prerequisites pass.
  - Every acceptance ID has at least one passing test case evidence.
  - No out-of-scope file modifications are present.
- Fail when:
  - Any scoped command fails.
  - Mojibake remains in scoped files.
  - Any non-text behavior change is detected.
  - Required test environment is missing (fail-fast as blocked, not pass).

## Regression Scope

- Auth route guard flow (`PermissionGuard`, login error path).
- Layout mobile sidebar button accessibility labels.
- Unauthorized route rendering.
- Error mapping consumers depending on `mapUserFacingErrorMessage`.

## Reporting Notes

- Record command outcomes and artifact paths in `test-report.md`.
- Keep tester independent from executor.
