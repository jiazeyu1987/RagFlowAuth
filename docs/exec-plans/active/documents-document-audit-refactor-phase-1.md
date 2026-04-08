# Documents / Document Audit Refactor Phase 1

## Context

The current documents/document-audit hotspot is concentrated in a backend manager and a frontend
page pair:

- `backend/services/documents/document_manager.py`
- `fronted/src/features/audit/useDocumentAuditPage.js`
- `fronted/src/pages/DocumentAudit.js`

The backend manager currently mixes preview payload building, watermark package creation, unified
download response construction, batch-download handling, and delete orchestration. The frontend
audit page still renders all tabs, filters, signature-manifest sections, and versions-modal markup
in one file while the hook still combines data loading, user-name resolution, and modal state.

That makes small changes to unified document behavior or audit-page rendering risky because one
edit can touch download policy, delete semantics, modal loading, and table rendering at once.

## In Scope

- backend document-manager decomposition
- frontend document-audit page and hook decomposition
- focused backend and frontend regression tests

## Out Of Scope

- backend API path or envelope changes
- watermark policy semantic changes
- upload approval redesign
- audit export redesign
- new fallback behavior

## Refactor Direction

1. Keep `DocumentManager` as the stable backend facade, but extract preview/download/delete support
   helpers into bounded modules.
2. Keep `DocumentAudit` as the stable page entry and `useDocumentAuditPage` as the stable hook
   facade, but split audit data/modal state and page rendering into focused helpers/components.
3. Extract page sections from `DocumentAudit.js` so the page shell stops owning all tab tables and
   versions-modal markup in one file.
4. Preserve current unified route contracts, audit page test ids, version-history behavior, and
   controlled-distribution download semantics.

## Acceptance Criteria

1. Backend document-management logic is no longer concentrated in the current manager alone.
2. Frontend document-audit page and hook are no longer single-file owners of all page state and
   rendering concerns.
3. Focused backend and frontend documents/document-audit tests pass after the refactor.

## Validation

- `python -m pytest backend/tests/test_documents_unified_router_unit.py`
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/audit/useDocumentAuditPage.test.js src/pages/DocumentAudit.test.js`
