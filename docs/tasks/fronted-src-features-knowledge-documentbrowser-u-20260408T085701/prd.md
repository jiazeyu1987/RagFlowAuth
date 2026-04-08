# Document Browser Hook Refactor PRD

- Task ID: `fronted-src-features-knowledge-documentbrowser-u-20260408T085701`
- Created: `2026-04-08T08:57:01`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js，拆分派生数据、页面动作与路由聚焦 effect，保持 DocumentBrowser 页面契约和现有 Jest 行为稳定`

## Goal

Decompose `useDocumentBrowserPage.js` so the page hook no longer directly owns derived tree/filter
state, page-level document actions, and location-driven focus behavior in one file, while
preserving the external contract consumed by `DocumentBrowser.js` and the current document browser
behavior.

## Scope

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- new bounded helper module(s) or child hook(s) under
  `fronted/src/features/knowledge/documentBrowser/`
- focused frontend tests:
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js`
  - `fronted/src/pages/DocumentBrowser.test.js`
- task artifacts under
  `docs/tasks/fronted-src-features-knowledge-documentbrowser-u-20260408T085701/`

## Non-Goals

- changing document browser API calls, transfer payloads, preview/download/delete semantics, or
  local storage keys
- changing `DocumentBrowser.js` or extracted page components beyond wiring needed to keep tests
  green
- redesigning the document-browser UI
- refactoring `useDocumentBrowserData.js`, `useDocumentBrowserTransfer.js`, or other existing child
  hooks beyond adapter-level changes

## Preconditions

- `fronted/` can run focused Jest tests through `npm test`
- `useDocumentBrowserPage()` remains the stable page-facing state/action contract
- existing document-browser hook and page Jest suites remain the source of truth for current
  behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- visible dataset filtering and folder/tree derived state
- quick-open, preview, download, delete, batch-download, and dataset expand/collapse actions
- user-reset, visible-dataset prefetch, and route-state focus effects
- document-browser hook and page Jest coverage

## Phase Plan

### P1: Split the document browser page hook into bounded helpers

- Objective: Move the densest responsibilities out of `useDocumentBrowserPage.js` without changing
  the page-facing return contract.
- Owned paths:
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
  - new helper module(s) or child hook(s) under
    `fronted/src/features/knowledge/documentBrowser/`
- Dependencies:
  - existing `useDocumentBrowserData`, `useDocumentBrowserPreferences`,
    `useDocumentBrowserSelection`, and `useDocumentBrowserTransfer`
  - current `DocumentBrowser.js` consumer expectations
- Deliverables:
  - slimmer composition hook
  - isolated helpers for derived state, page actions, and route/effect orchestration
  - preserved external return keys and behavior

### P2: Focused regression validation and tranche evidence

- Objective: Prove the hook refactor preserves current document-browser behavior and record
  reviewable evidence.
- Owned paths:
  - focused Jest tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - passing focused Jest suites
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `useDocumentBrowserPage.js` becomes a composition-oriented hook instead of directly
  embedding derived dataset/tree state, page actions, and route-focus effect orchestration in one
  file.
- P1-AC2: bounded local helpers own repeated dataset resolution, folder-path expansion, and action
  coordination so future document-browser changes have better locality.
- P1-AC3: `DocumentBrowser.js` and extracted page components continue consuming the same
  `useDocumentBrowserPage()` contract without fallback branches or behavior changes.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused document-browser hook and page Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, changed paths, verified acceptance ids, and
  bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids are backed by evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `DocumentBrowser.js` continues consuming `useDocumentBrowserPage()` without contract drift.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the public return shape of
  `useDocumentBrowserPage()`
- the hook cannot be decomposed without introducing fallback paths for missing dataset, folder,
  preview, or route-focus state
