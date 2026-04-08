# Document Browser Page Refactor Test Plan

- Task ID: `fronted-src-pages-documentbrowser-js-usedocument-20260408T084722`
- Created: `2026-04-08T08:47:22`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/pages/DocumentBrowser.js，拆分快捷知识库、筛选栏、目录工作区与状态区块，保持 useDocumentBrowserPage 契约和现有 Jest 行为稳定`

## Test Scope

Validate that the bounded page refactor preserves:

- quick-dataset rendering and quick-open actions
- filter input / clear / recent-keyword rendering
- document-browser route-page consumption of the existing `useDocumentBrowserPage` contract

Out of scope:

- real-browser preview/download/delete behavior
- live backend integration for Ragflow documents
- refactoring the underlying `useDocumentBrowserPage.js` hook

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend: CRA/Jest via `npm test`
- Test runtime: mocked page hook and mocked child components in the focused Jest suites

## Accounts and Fixtures

- tests rely on mocked `useDocumentBrowserPage` state and mocked child components
- no live backend, browser automation, or seed data is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js`
  - Expected success signal: focused document-browser hook and page suites pass in a single
    non-watch Jest run

## Test Cases

### T1: Document browser page and page-hook regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js`
- Expected: page component extraction preserves quick-open, filter, and workspace rendering without
  changing the current page-hook wiring

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend document browser | page decomposition preserves page-hook wiring and quick/filter interactions | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

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
  - page/page-hook behavior stays stable under the existing and updated tests
- Fail when:
  - the command fails
  - page extraction breaks quick-open, filter, or current route-page integration behavior

## Regression Scope

- `fronted/src/pages/DocumentBrowser.js`
- new component/helper module(s) under `fronted/src/features/knowledge/documentBrowser/`
- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
