# PRD

- Task ID: `task-3bb2aeeff3-20260414T090034`
- Created: `2026-04-14T09:00:34`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Fix frontend garbled text, convert Chinese copy to English, and make wording more formal.`

## Goal

Deliver one bounded frontend copy cleanup that:
- removes confirmed mojibake text in high-impact shared UI entry points,
- converts targeted user-facing copy to formal English,
- keeps behavior unchanged (text-only updates, no fallback logic).

## Scope

In scope files (only):
- `fronted/src/pages/Tools.js`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/App.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/components/Layout.js`
- `fronted/src/components/layout/LayoutHeader.js`
- `fronted/src/components/layout/LayoutSidebar.js`
- `fronted/src/features/auth/useLoginPage.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`
- `fronted/src/pages/Unauthorized.js`
- `fronted/src/pages/Tools.test.js`
- `fronted/e2e/tests/docs.approval-config.spec.js` (fix garbled test title/assertion text only)

Linked tests in scope:
- `fronted/src/components/PermissionGuard.test.js`
- `fronted/src/features/auth/useLoginPage.test.js`
- `fronted/src/pages/LoginPage.test.js`
- `fronted/src/pages/Tools.test.js`
- `fronted/src/shared/errors/userFacingErrorMessages.test.js`
- `fronted/e2e/tests/rbac.unauthorized.spec.js`
- `fronted/e2e/tests/docs.approval-config.spec.js`

## Non-Goals

- Full-repo i18n migration across all `fronted/src` and `fronted/e2e`.
- Refactor to i18n framework, locale switch, or translation infrastructure.
- Any API, permission, routing, or business-logic behavior changes.
- Bulk update of unrelated Chinese content in feature pages not listed in Scope.

## Preconditions

- `fronted/node_modules` is installed (`Set-Location fronted; npm install` completed).
- Playwright browsers are available for local run (`Set-Location fronted; npx playwright install` completed).
- Frontend test runtime can boot locally (React test environment and Playwright runtime available).
- For docs E2E spec execution, required doc test environment/bootstrap data exists.

Fail-fast rule:
- If any precondition is missing, stop immediately and record the exact missing item and impact in `task-state.json.blocking_prereqs`.

## Impacted Areas

- App-level loading and permission guard copy.
- Layout accessibility labels (mobile sidebar open/close/toggle controls).
- Login failure fallback copy.
- Central backend-error-to-user-message mapper.
- Unauthorized page formal English copy.
- One known mojibake E2E test case (`docs.approval-config.spec.js`) string literals.

## Phase Plan

### P1: Text Baseline and Formal English Copy Contract

- Objective: finalize exact replacement text set for the scoped files and remove confirmed mojibake strings.
- Owned paths:
  - `fronted/src/App.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/components/Layout.js`
  - `fronted/src/components/layout/LayoutHeader.js`
  - `fronted/src/components/layout/LayoutSidebar.js`
  - `fronted/src/features/auth/useLoginPage.js`
  - `fronted/src/shared/errors/userFacingErrorMessages.js`
  - `fronted/src/pages/Unauthorized.js`
- Dependencies: existing route/auth/error-map contracts remain unchanged.
- Deliverables: text-only diffs with formal English copy and no mojibake literals in scoped files.

### P2: Test Alignment and Real-Browser Validation

- Objective: align linked tests with finalized copy and verify behavior in unit + Playwright coverage.
- Owned paths:
  - `fronted/src/components/PermissionGuard.test.js`
  - `fronted/src/features/auth/useLoginPage.test.js`
  - `fronted/src/pages/LoginPage.test.js`
  - `fronted/src/shared/errors/userFacingErrorMessages.test.js`
  - `fronted/e2e/tests/rbac.unauthorized.spec.js`
  - `fronted/e2e/tests/docs.approval-config.spec.js`
- Dependencies: P1 completed; test environment preconditions satisfied.
- Deliverables: passing scoped test commands with recorded evidence.

## Phase Acceptance Criteria

### P1

- P1-AC1: No garbled/mojibake user-facing strings remain in the scoped source files.
- P1-AC2: All changed user-facing strings in scoped source files are English and formal in tone.
- P1-AC3: Changes are text-only (string/comment/test-label updates), with no control-flow or API contract changes.
- Evidence expectation: diff review + targeted grep evidence over scoped paths.

### P2

- P2-AC1: Scoped unit tests pass for updated copy assertions.
- P2-AC2: Real-browser Playwright validation passes for unauthorized page visibility and approval-config spec string checks.
- P2-AC3: This task does not introduce additional edits outside Scope and linked tests.
- Evidence expectation: command outputs and Playwright artifacts (report/trace/screenshot/video as available).

## Done Definition

- P1 and P2 are completed.
- P1-AC1..P1-AC3 and P2-AC1..P2-AC3 each have evidence in `execution-log.md` and/or `test-report.md`.
- No fallback behavior, mock success path, or silent downgrade is introduced.

## Blocking Conditions

- Scoped file list changes without explicit user approval.
- Missing Node/Playwright dependencies or missing docs E2E prerequisites.
- Any required copy decision is ambiguous and materially affects acceptance (must ask user, then proceed).
- Test command fails due environment gap that prevents acceptance validation.
