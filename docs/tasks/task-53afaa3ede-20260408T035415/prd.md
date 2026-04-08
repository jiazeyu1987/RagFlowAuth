# Document Browser Preview Refactor PRD

- Task ID: `task-53afaa3ede-20260408T035415`
- Created: `2026-04-08T03:54:15`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：完成系统重构计划最后一阶段，拆分文档浏览器与文档预览前端模块，保持现有行为并补齐验证。`

## Goal

Finish the last planned frontend refactor tranche by decomposing the oversized document-browser
page hook and document-preview modal into smaller, more cohesive units while preserving the
existing user-visible behavior for dataset browsing, preview loading, transfer operations, and
preview rendering.

## Scope

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- new document-browser helper hooks or utilities under
  `fronted/src/features/knowledge/documentBrowser/`
- `fronted/src/shared/documents/preview/DocumentPreviewModal.js`
- new preview helper hooks or renderer modules under
  `fronted/src/shared/documents/preview/`
- focused frontend tests for document-browser and preview behavior
- `docs/exec-plans/active/document-browser-preview-refactor-phase-1.md`

## Non-Goals

- route/navigation changes
- permission-model changes
- backend API contract changes
- redesigning the document-browser page layout
- adding fallback preview behavior for unsupported or missing payloads
- large rewrites of dataset-panel or transfer-dialog presentation

## Preconditions

- Existing document-browser Jest tests can run in the frontend workspace.
- `documentBrowserApi`, `knowledgeApi`, and `documentsApi` contracts remain unchanged.
- `DocumentPreviewModal` continues to receive a valid `documentApi` prop from callers.
- Current preview helper modules under `fronted/src/shared/preview/` remain importable.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- document-browser dataset loading, filter history, usage tracking, selection, and transfer flows
- preview modal loading lifecycle for OnlyOffice, HTML, PDF, image, text, and Excel/Docx previews
- object URL creation and cleanup behavior in preview flows
- page-level consumer `fronted/src/pages/DocumentBrowser.js`
- existing tests:
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js`
  - `fronted/src/pages/DocumentBrowser.test.js`
  - `fronted/src/shared/documents/preview/OnlyOfficeViewer.test.js`
  - `fronted/src/shared/documents/preview/watermarkOverlay.test.js`

## Phase Plan

### P1: Decompose document-browser page state

- Objective: Split document-browser responsibilities into smaller browser-domain hooks/helpers
  without changing the public page-hook contract used by `DocumentBrowser.js`.
- Owned paths:
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
  - new helper modules under `fronted/src/features/knowledge/documentBrowser/`
  - `fronted/src/pages/DocumentBrowser.js` only if adapter wiring is needed
- Dependencies:
  - existing browser components and constants
  - current `useAuth`, `knowledgeApi`, `documentBrowserApi`, and `documentsApi` behavior
- Deliverables:
  - extracted document-browser sub-hooks/helpers for preferences, data loading, and action flows
  - slimmer orchestration hook that preserves the existing return shape

### P2: Decompose document-preview modal lifecycle and renderer

- Objective: Split preview loading/state lifecycle from preview content rendering so new formats
  or lifecycle fixes stop accumulating in one modal file.
- Owned paths:
  - `fronted/src/shared/documents/preview/DocumentPreviewModal.js`
  - new helper modules under `fronted/src/shared/documents/preview/`
- Dependencies:
  - existing preview helpers such as `loadDocumentPreview`
  - current preview modal props and OnlyOffice integration
- Deliverables:
  - extracted preview-session hook or helper
  - extracted preview content renderer component/helper
  - preserved object URL cleanup and existing supported preview branches

### P3: Focused regression coverage and task evidence

- Objective: Prove the bounded refactor preserved the targeted browser and preview behaviors.
- Owned paths:
  - `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js`
  - `fronted/src/pages/DocumentBrowser.test.js`
  - `fronted/src/shared/documents/preview/DocumentPreviewModal.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused Jest coverage for browser and preview flows
  - execution and test evidence for all acceptance ids

## Phase Acceptance Criteria

### P1

- P1-AC1: `useDocumentBrowserPage.js` no longer directly owns all major responsibilities for
  storage-backed preferences, document loading, folder navigation, and batch/transfer actions in
  one file.
- P1-AC2: `DocumentBrowser.js` and existing browser components can continue using the page hook
  without a breaking contract change.
- P1-AC3: dataset usage tracking, recent keyword persistence, document loading, delete, batch
  download, and transfer behavior remain stable after decomposition.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `DocumentPreviewModal.js` no longer mixes preview loading orchestration and all format
  render branches in one monolithic component body.
- P2-AC2: OnlyOffice, PDF, HTML, image, text/markdown/CSV, and Excel/Docx preview branches
  continue to render through explicit preview-specific logic after extraction.
- P2-AC3: object URL cleanup and modal close/reset behavior remain explicit and verifiable.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused frontend Jest suites pass against the final code state.
- P3-AC2: task artifacts record the commands run, acceptance coverage, and any remaining bounded
  risks.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- The document-browser page and preview modal keep their existing externally observable behavior.
- The remaining system-refactor plan no longer has an unfinished document-browser/preview tranche.

## Blocking Conditions

- focused frontend validation cannot run in the current workspace
- decomposition would require changing backend preview or document-transfer contracts
- preserving current preview behavior would require silent downgrade or fallback branches
- preview state cleanup cannot be kept explicit after extraction
