# Document Browser Preview Refactor Phase 1

## Context

The remaining unfinished tranche in the active system refactor plan is the document browser and
preview frontend hotspot. Two files still concentrate too many responsibilities:

- `fronted/src/features/knowledge/documentBrowser/useDocumentBrowserPage.js`
- `fronted/src/shared/documents/preview/DocumentPreviewModal.js`

The browser hook currently mixes dataset loading, tree state, localStorage-backed preferences,
selection, batch actions, transfer orchestration, and preview launch state. The preview modal
mixes responsive shell behavior, preview loading, object URL lifecycle, PDF rendering, OnlyOffice
setup, copy-protection wiring, and multi-format rendering dispatch.

That combination makes small behavior changes risky because one edit can affect unrelated flows.

## In Scope

- document-browser page-hook decomposition
- preview modal lifecycle/render decomposition
- focused frontend regression tests

## Out Of Scope

- backend API redesign
- route/navigation or permission-model changes
- visual restyling of the document-browser page
- adding new preview formats

## Refactor Direction

1. Extract document-browser sub-hooks/helpers around:
   - storage-backed preferences and usage tracking
   - dataset/document loading
   - selection, batch download, and transfer orchestration
2. Keep `useDocumentBrowserPage` as a stable facade that still returns the current page contract.
3. Extract preview-session loading/state management from `DocumentPreviewModal`.
4. Extract preview content rendering into a dedicated renderer/helper so format branches stop
   accumulating inside the modal shell.
5. Add focused tests for the preview modal because that area currently has no direct coverage.

## Acceptance Criteria

1. `useDocumentBrowserPage` becomes an orchestration layer instead of the single owner of all
   browser responsibilities.
2. `DocumentPreviewModal` keeps modal-shell concerns separate from preview loading/render logic.
3. Existing document-browser behaviors and key preview render paths remain stable under focused
   Jest coverage.

## Validation

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/documentBrowser/useDocumentBrowserPage.test.js src/pages/DocumentBrowser.test.js src/shared/documents/preview/DocumentPreviewModal.test.js`
