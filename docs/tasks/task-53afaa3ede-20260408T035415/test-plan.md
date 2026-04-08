# Document Browser Preview Refactor Test Plan

- Task ID: `task-53afaa3ede-20260408T035415`
- Created: `2026-04-08T03:54:15`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：完成系统重构计划最后一阶段，拆分文档浏览器与文档预览前端模块，保持现有行为并补齐验证。`

## Test Scope

Validate that the bounded frontend refactor preserves:

- document-browser dataset loading and browsing orchestration
- selection, batch download, delete, and transfer flows
- preview modal loading paths and render dispatch for key preview types
- preview modal reset and object URL lifecycle behavior relevant to the refactor

Out of scope:

- backend API integration beyond mocked contracts
- route/navigation behavior
- real-browser OnlyOffice end-to-end validation
- visual redesign checks

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Frontend: Node.js/npm with Jest via `react-scripts test`
- Test mode: focused unit/component suites with mocked browser APIs and mocked document services

## Accounts and Fixtures

- tests use mocked `useAuth`, `documentBrowserApi`, `knowledgeApi`, `documentsApi`, and preview
  service methods
- preview tests may mock `URL.createObjectURL`, `URL.revokeObjectURL`, and loader helpers
- if Jest or npm is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js src/shared/documents/preview/DocumentPreviewModal.test.js`
  - Expected success signal: all focused browser and preview suites pass

## Test Cases

### T1: Document-browser behavior remains stable after hook decomposition

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js`
- Expected: the page hook still drives dataset loading, delete, batch download, transfer, and page
  rendering flows without a breaking contract change

### T2: Preview lifecycle and render dispatch remain stable after modal decomposition

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/shared/documents/preview/DocumentPreviewModal.test.js`
- Expected: the modal still routes preview loading to the right preview path, renders the expected
  preview content branch, and cleans up transient object URLs on close/unmount

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | document browser | page hook decomposition preserves browser actions and page contract | unit/component | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | document preview | modal decomposition preserves preview loading, rendering, and cleanup | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run focused Jest suites against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - document-browser and preview responsibilities are decomposed without breaking the current
    page-hook or modal contracts
- Fail when:
  - the focused Jest command fails
  - preview render paths or cleanup behavior regress
  - the browser hook contract changes in a way that breaks existing consumers

## Regression Scope

- `fronted/src/features/knowledge/documentBrowser/*`
- `fronted/src/pages/DocumentBrowser.js`
- `fronted/src/shared/documents/preview/*`
- `fronted/src/shared/preview/*`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether each suite passed.
