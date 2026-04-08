# PRD

- Task ID: `e2e-bat-e2e-20260408T134710`
- Created: `2026-04-08T13:47:10`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Add the missing login-related E2E coverage needed by the doc E2E batch.`
- Follow-up Request: `Continue fixing the remaining existing doc E2E failures one by one.`

## Goal

Ensure the doc E2E batch runner remains fully wired for login coverage and stabilize the remaining existing doc E2E failures so the documentation batch run reflects the real current API and UI behavior instead of stale response-shape assumptions or batch-runner false failures.

## Scope

- Doc E2E test suite executed by `鏂囨。E2E鑷姩娴嬭瘯.bat` and `scripts/run_doc_e2e.py`.
- Doc E2E Playwright specs under `fronted/e2e/tests/docs*.spec.js`.
- Doc E2E helpers under `fronted/e2e/helpers/` that encode current backend response expectations.
- Doc E2E manifest wiring and batch-runner behavior that control which specs execute and how results are collected.

## Non-Goals

- Do not alter backend auth logic, approval logic, password policies, or production API contracts.
- Do not change non-doc Playwright suites (for example `smoke.*` or `integration.*`), except where a shared helper update is strictly required and does not change product behavior.
- Do not introduce fallback or mock-only paths that hide real doc runtime failures.

## Preconditions

- `npx` is available in PATH.
- Playwright is installed in `fronted` and the docs config can start the real frontend and backend.
- Doc E2E bootstrap is runnable and provides required accounts:
  - `scripts/bootstrap_doc_test_env.py` must succeed.
  - `data/e2e/doc_auth.db` is writable and used via `E2E_TEST_DB_PATH`.
- Doc E2E manifest exists and is valid at `doc/e2e/manifest.json`.
- RAGFlow availability if `E2E_BOOTSTRAP_REQUIRE_RAGFLOW=1` (fail fast if unavailable).

If any prerequisite is missing, execution must stop and record the blocker.

## Impacted Areas

- `鏂囨。E2E鑷姩娴嬭瘯.bat`
- `scripts/run_doc_e2e.py`
- `doc/e2e/manifest.json`
- `fronted/playwright.docs.config.js`
- `fronted/e2e/tests/docs*.spec.js`
- `fronted/e2e/helpers/*`

## Phase Plan

### P1: Add doc-login coverage and wire into doc batch runner

- Objective: Ensure the doc E2E batch run includes a complete login flow spec and fails fast when manifest wiring is missing.
- Owned paths:
  - `doc/e2e/manifest.json`
  - `fronted/e2e/tests/docs.login.spec.js`
  - Any doc E2E helper updates strictly required for login coverage
- Dependencies:
  - Doc bootstrap accounts and E2E environment vars.
  - Playwright docs config.
- Deliverables:
  - New doc login spec covering success and failure messaging.
  - Manifest updated to include the new spec so the batch runner executes it.

### P2: Align shared doc E2E helpers and specs with current response envelopes

- Objective: Remove stale test assumptions about top-level `request_id`, `user_id`, `group_id`, and folder ids so doc specs assert against the real current backend envelopes.
- Owned paths:
  - `fronted/e2e/helpers/docRealFlow.js`
  - `fronted/e2e/helpers/permissionGroupsFlow.js`
  - `fronted/e2e/helpers/userLifecycleFlow.js`
  - `fronted/e2e/helpers/securityToolsFlow.js`
  - `fronted/e2e/helpers/searchChatFlow.js`
  - Affected `fronted/e2e/tests/docs*.spec.js` files that currently parse stale envelope shapes directly
- Dependencies:
  - Current backend response envelopes for operation approvals, users, permission groups, and permission-group folders.
  - Existing doc bootstrap fixtures and real browser runtime.
- Deliverables:
  - Shared helper parsing aligned to the current API contracts.
  - Affected doc specs updated to consume `request`, `user`, `result`, and `folder` envelopes correctly.

### P3: Fix assertion-specific doc specs to match current seeded runtime behavior

- Objective: Update doc specs whose failures are not envelope-related, but instead depend on current action response nesting or seeded initial settings.
- Owned paths:
  - `fronted/e2e/tests/docs.approval-center.spec.js`
  - `fronted/e2e/tests/docs.notification-settings.spec.js`
- Dependencies:
  - Current approval action response envelope.
  - Current notification bootstrap seed state.
- Deliverables:
  - Approval-center doc spec asserts the current withdraw action payload correctly.
  - Notification-settings doc spec validates current seeded rule defaults before performing save, retry, and dispatch flows.

### P4: Restore full doc batch fidelity and verify the complete documentation run

- Objective: Ensure the batch command reports the real suite result without false failures caused by per-spec runner churn, then verify the whole manifest passes.
- Owned paths:
  - `scripts/run_doc_e2e.py`
  - `fronted/playwright.docs.config.js`
  - `doc/test/reports/doc_e2e_report_latest.md` (evidence only)
- Dependencies:
  - All doc specs in manifest are green in targeted validation.
  - Batch-runner execution strategy is stable against the real local ports and runtime.
- Deliverables:
  - Full doc batch run exits successfully.
  - Latest doc report shows the entire manifest green.

## Phase Acceptance Criteria

### P1

- P1-AC1: A doc E2E login spec exists under `fronted/e2e/tests/docs*.spec.js` that validates a successful UI login using the real doc bootstrap account(s).
- P1-AC2: The doc login spec validates at least one failure path with user-visible error messaging (for example wrong password or disabled account) using the real doc E2E runtime.
- P1-AC3: `doc/e2e/manifest.json` exists and includes the login spec so `鏂囨。E2E鑷姩娴嬭瘯.bat` runs it via `scripts/run_doc_e2e.py`.
- Evidence expectation: A doc E2E report entry lists the login spec and shows pass results.

### P2

- P2-AC1: Doc upload, browser, global-search, chat, knowledge-base, and role-scope specs extract approval request ids from the current `OperationApprovalRequestEnvelope` shape and pass targeted browser validation.
- P2-AC2: Doc user-management, password-change, and tools specs extract created user ids from the current `UserEnvelope` shape and pass targeted browser validation.
- P2-AC3: Doc permission-groups, role-permission-menu, and tools specs extract permission-group ids and folder ids from the current `result` or `folder` envelopes and pass targeted browser validation.
- Evidence expectation: Grouped Playwright runs covering the affected specs pass without modifying production API contracts.

### P3

- P3-AC1: `docs.approval-center.spec.js` asserts withdraw success against the current approval action envelope and passes targeted browser validation.
- P3-AC2: `docs.notification-settings.spec.js` matches the current seeded notification rule defaults and still validates save, retry, and dispatch behavior in the real browser runtime.
- Evidence expectation: Targeted Playwright runs for the assertion-specific specs pass with current bootstrap data.

### P4

- P4-AC1: `python scripts/run_doc_e2e.py --repo-root D:\ProjectPackage\RagflowAuth` completes with exit code 0 and produces a PASS report.
- P4-AC2: `doc/test/reports/doc_e2e_report_latest.md` lists the full manifest and marks every doc spec PASS, without false failures caused by batch-runner port or process churn.
- Evidence expectation: Latest doc batch report plus full-run command output captured in `execution-log.md` and `test-report.md`.

## Done Definition

- All P1-P4 acceptance criteria are completed with evidence recorded in `execution-log.md` and verified by independent testing.
- Doc E2E batch runner executes the full manifest and produces a passing report.
- No fallback or mock-only test path was introduced to hide real failures.

## Blocking Conditions

- `doc/e2e/manifest.json` remains missing or invalid.
- Doc bootstrap script or required accounts fail to initialize.
- Playwright or `npx` unavailable.
- Required external services (for example RAGFlow when required) are unavailable.
- Current backend or frontend contracts drift again during execution such that the doc suite no longer matches the repo state under test.
