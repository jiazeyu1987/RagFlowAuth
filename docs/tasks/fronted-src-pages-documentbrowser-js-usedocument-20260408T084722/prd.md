# Document Browser Page Refactor PRD

- Task ID: `fronted-src-pages-documentbrowser-js-usedocument-20260408T084722`
- Created: `2026-04-08T08:47:22`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 fronted/src/pages/DocumentBrowser.js，拆分快捷知识库、筛选栏、目录工作区与状态区块，保持 useDocumentBrowserPage 契约和现有 Jest 行为稳定`

## Goal

Decompose `DocumentBrowser.js` so the route page no longer mixes mobile layout handling, quick
dataset cards, filter controls, workspace layout, breadcrumb rendering, and modal wiring in one
file, while preserving the existing `useDocumentBrowserPage` contract and current document browser
behavior.

## Scope

- `fronted/src/pages/DocumentBrowser.js`
- new bounded component/helper module(s) under `fronted/src/features/knowledge/documentBrowser/`
- focused frontend tests:
  - `fronted/src/pages/DocumentBrowser.test.js`
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js`
- task artifacts under
  `docs/tasks/fronted-src-pages-documentbrowser-js-usedocument-20260408T084722/`

## Non-Goals

- changing document browser API calls, dataset/document transfer behavior, or preview/download/delete
  semantics
- refactoring `useDocumentBrowserPage.js` in this tranche
- redesigning `DatasetPanel`, `FolderTree`, `TransferDialog`, or `BatchTransferProgress`
- changing route wiring or preview modal contracts

## Preconditions

- `fronted/` can run focused Jest tests through `npm test`
- `useDocumentBrowserPage()` remains the stable page-facing state/action contract
- existing document browser page and page-hook Jest suites remain the source of truth for current
  behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- quick-dataset cards and empty state rendering
- dataset filter input, clear button, and recent-keyword chip rendering
- folder tree / breadcrumb / dataset workspace page composition
- page-level loading, error, and empty-state rendering
- document browser page Jest coverage

## Phase Plan

### P1: Split the document browser route page into focused render components

- Objective: Move the major render sections out of `DocumentBrowser.js` while keeping the route page
  as a composition shell over `useDocumentBrowserPage`.
- Owned paths:
  - `fronted/src/pages/DocumentBrowser.js`
  - new component/helper module(s) under `fronted/src/features/knowledge/documentBrowser/`
  - focused Jest tests listed above as needed
- Dependencies:
  - existing `useDocumentBrowserPage` contract
  - current `DatasetPanel`, `FolderTree`, `TransferDialog`, and preview modal integrations
- Deliverables:
  - slimmer page composition layer
  - extracted render components for quick datasets, filters, and workspace sections
  - unchanged page-level behavior

### P2: Focused frontend regression validation and tranche evidence

- Objective: Prove the bounded page refactor preserved current document-browser behavior.
- Owned paths:
  - focused tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - focused frontend regression coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `DocumentBrowser.js` no longer directly owns the quick-dataset cards, filter block,
  workspace layout, breadcrumb block, and modal wiring in one large file.
- P1-AC2: the page continues to consume the same `useDocumentBrowserPage` contract without
  page-level behavior changes.
- P1-AC3: loading, empty, quick-open, and filter actions continue surfacing the existing states
  without introducing fallback branches.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused document-browser page and page-hook Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `DocumentBrowser.js` remains the stable route page consuming `useDocumentBrowserPage()`.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the `useDocumentBrowserPage` return contract
- page extraction would require fallback behavior for missing dataset, folder, preview, or transfer
  state
