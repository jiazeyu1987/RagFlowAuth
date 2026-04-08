# Document Browser Hook Refactor Test Plan

- Task ID: `fronted-src-features-knowledge-documentbrowser-u-20260408T085701`
- Created: `2026-04-08T08:57:01`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js，拆分派生数据、页面动作与路由聚焦 effect，保持 DocumentBrowser 页面契约和现有 Jest 行为稳定`

## Test Scope

Validate that the bounded hook refactor preserves:

- dataset/document loading and transfer behavior
- delete and batch-download action routing
- keyword persistence, quick-open behavior, and page-facing contract stability

Out of scope:

- real browser preview/download/delete validation
- live backend integration against Ragflow
- broader page shell refactors outside the existing focused page and hook suites

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend runtime: CRA/Jest via `npm test`
- Test runtime: mocked `useAuth`, mocked document APIs, and focused document-browser page/hook
  suites already in the repo

## Accounts and Fixtures

- tests rely on mocked auth state, mocked API responses, and localStorage setup
- no live backend, browser automation, or seeded database is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js`
  - Expected success signal: all focused document-browser hook and page suites pass in one
    non-watch run

## Test Cases

### T1: Document browser hook and page regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js`
- Expected: the refactored hook preserves current loading, action routing, quick-open, and page
  integration without changing the existing route-page contract

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend document browser | hook decomposition preserves current loading, actions, quick-open, and page wiring | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused Jest command against the real repo state in
  `fronted/`
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the focused Jest command succeeds
  - the current hook/page contract remains compatible with the existing and updated tests
- Fail when:
  - the command fails
  - the refactor changes required return keys, breaks current action routing, or breaks page
    integration

## Regression Scope

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- new helper module(s) or child hook(s) under
  `fronted/src/features/knowledge/documentBrowser/`
- `fronted/src/pages/DocumentBrowser.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command, whether it passed, and any remaining risk around uncovered route-focus
  timing branches.
