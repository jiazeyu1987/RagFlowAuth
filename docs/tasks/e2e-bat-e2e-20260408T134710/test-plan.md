# Test Plan

- Task ID: `e2e-bat-e2e-20260408T134710`
- Created: `2026-04-08T13:47:10`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Add the missing login-related E2E coverage needed by the doc E2E batch.`
- Follow-up Request: `Continue fixing the remaining existing doc E2E failures one by one.`

## Test Scope

Validate the full doc E2E stabilization path:
- Existing login coverage remains present and green in the real doc runtime.
- Shared doc E2E helpers and specs consume the current backend envelopes for approval requests, users, permission groups, and permission-group folders.
- Assertion-specific doc specs reflect the current action payloads and seeded notification defaults.
- The full doc batch command reports the real suite result without per-spec runner false failures.

Out of scope:
- Backend auth or approval algorithm changes.
- Production API contract changes made only to preserve stale test assumptions.
- Non-doc Playwright suites unless a shared helper update is strictly required and does not change product behavior.

## Environment

- OS: Windows (batch entry path must remain valid).
- Services: backend and frontend started by Playwright docs config or by the stabilized doc batch runner.
- Env vars required by the doc E2E runner:
  - `E2E_FRONTEND_BASE_URL` (default: `http://127.0.0.1:33002`)
  - `E2E_BACKEND_BASE_URL` (default: `http://127.0.0.1:38002`)
  - `E2E_TEST_DB_PATH` (default: `data/e2e/doc_auth.db`)
  - `E2E_BOOTSTRAP_SCRIPT` (default: `scripts/bootstrap_doc_test_env.py`)
  - `E2E_BOOTSTRAP_REQUIRE_RAGFLOW=1` (must fail fast if unavailable)
- Tools: `npx`, Playwright, Python.

## Accounts and Fixtures

- Doc bootstrap accounts created by `scripts/bootstrap_doc_test_env.py` (company admin, sub-admin, operator, viewer, reviewer, uploader, and any seeded doc fixtures).
- Notification, approval, training, and knowledge fixtures seeded by the same bootstrap summary consumed by doc specs.
- Any extra test-created users, groups, folders, requests, or files must be created and cleaned up through the real API helpers. Do not use mock-only bypasses.

If any required account or fixture is missing, fail fast and record the prerequisite.

## Commands

1. Baseline login validation:
   - `npx playwright test --config playwright.docs.config.js e2e/tests/docs.login.spec.js --workers=1`
   - Expected: exit code 0 and the login spec passes.

2. Approval-request envelope validation group:
   - `npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-upload.spec.js e2e/tests/docs.document-browser.spec.js e2e/tests/docs.knowledge-base-config.spec.js e2e/tests/docs.global-search.spec.js e2e/tests/docs.chat.spec.js e2e/tests/docs.document-upload-publish.spec.js e2e/tests/docs.role.knowledge-scope.spec.js e2e/tests/docs.role.data-isolation.spec.js --workers=1`
   - Expected: exit code 0 and every spec in the group passes.

3. User and permission-group envelope validation group:
   - `npx playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js e2e/tests/docs.password-change.spec.js e2e/tests/docs.permission-groups.spec.js e2e/tests/docs.role.permission-menu.spec.js e2e/tests/docs.tools.spec.js --workers=1`
   - Expected: exit code 0 and every spec in the group passes.

4. Assertion-specific validation group:
   - `npx playwright test --config playwright.docs.config.js e2e/tests/docs.approval-center.spec.js e2e/tests/docs.notification-settings.spec.js --workers=1`
   - Expected: exit code 0 and both specs pass.

5. Full doc batch run:
   - `python scripts/run_doc_e2e.py --repo-root D:\ProjectPackage\RagflowAuth`
   - Or via `鏂囨。E2E鑷姩娴嬭瘯.bat`
   - Expected: exit code 0 and `doc/test/reports/doc_e2e_report_latest.md` reports PASS for the full manifest.

## Test Cases

### T1: Doc login succeeds for bootstrap admin

- Covers: P1-AC1
- Level: e2e
- Command: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.login.spec.js --workers=1`
- Expected: UI reaches the authenticated landing layout after real login.

### T2: Doc login failure shows user-visible error messaging

- Covers: P1-AC2
- Level: e2e
- Command: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.login.spec.js --workers=1`
- Expected: Login page displays a non-empty error message for the invalid-credential or disabled-account scenario.

### T3: Manifest wiring includes the login spec in the doc batch

- Covers: P1-AC3
- Level: e2e
- Command: `python scripts/run_doc_e2e.py --repo-root D:\ProjectPackage\RagflowAuth`
- Expected: `doc/test/reports/doc_e2e_report_latest.md` lists the login spec in the executed manifest.

### T4: Approval-request envelope group passes against current `request` payloads

- Covers: P2-AC1
- Level: e2e
- Command: command group 2 above
- Expected: Each affected spec reads request ids from the current approval request envelope and completes its real browser flow.

### T5: User envelope group passes against current `user` payloads

- Covers: P2-AC2
- Level: e2e
- Command: command group 3 above
- Expected: Each affected spec reads created user ids from the current user envelope and completes its real browser flow.

### T6: Permission-group and folder envelope group passes against current `result` and `folder` payloads

- Covers: P2-AC3
- Level: e2e
- Command: command group 3 above
- Expected: Each affected spec reads group ids and folder ids from the current envelopes and completes its real browser flow.

### T7: Assertion-specific specs match the current runtime behavior

- Covers: P3-AC1, P3-AC2
- Level: e2e
- Command: command group 4 above
- Expected: Approval withdraw asserts `result.status`, and notification settings match the seeded defaults while still validating save, retry, and dispatch flows.

### T8: Full doc batch run is green and free of per-spec runner false failures

- Covers: P4-AC1, P4-AC2
- Level: e2e
- Command: `python scripts/run_doc_e2e.py --repo-root D:\ProjectPackage\RagflowAuth`
- Expected: Latest report lists the full manifest and every doc spec is PASS.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Doc login | Successful admin login via UI | e2e | P1-AC1 | Playwright trace/report |
| T2 | Doc login | Failure message for invalid or blocked login | e2e | P1-AC2 | Playwright trace/report |
| T3 | Doc batch manifest | Login spec is wired into the batch manifest | e2e | P1-AC3 | Latest doc batch report |
| T4 | Approval request envelopes | Request-bearing doc specs read current `request` payloads | e2e | P2-AC1 | Grouped Playwright run output |
| T5 | User envelopes | User-bearing doc specs read current `user` payloads | e2e | P2-AC2 | Grouped Playwright run output |
| T6 | Permission-group envelopes | Group and folder doc specs read current `result` and `folder` payloads | e2e | P2-AC3 | Grouped Playwright run output |
| T7 | Assertion-specific docs | Approval-center and notification-settings match current runtime behavior | e2e | P3-AC1, P3-AC2 | Grouped Playwright run output |
| T8 | Full doc batch | Full manifest passes without runner false failures | e2e | P4-AC1, P4-AC2 | Latest doc batch report |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. Use real browser sessions and record evidence from Playwright traces, videos, screenshots, or equivalent outputs.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - All test cases T1-T8 pass and evidence is recorded.
  - The latest doc batch report is PASS for the entire manifest.
- Fail when:
  - Any test case fails.
  - Any required prerequisite is missing.
  - The batch run still reports false failures due to unstable per-spec runner behavior.

## Regression Scope

- Doc E2E specs that parse approval, user, permission-group, or folder responses.
- Doc E2E helpers shared by the affected specs.
- Doc E2E batch-runner scripts, Playwright docs config, and manifest execution wiring.

## Reporting Notes

Write results to `test-report.md` and attach evidence references for Playwright outputs and the latest doc batch report.
