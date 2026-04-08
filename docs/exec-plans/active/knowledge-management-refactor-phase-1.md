# Knowledge Management Refactor Phase 1

## Context

The current knowledge-management hotspot is concentrated in a backend manager and a frontend page
pair:

- `backend/services/knowledge_management/manager.py`
- `fronted/src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.js`
- `fronted/src/pages/KnowledgeBases.js`

The backend manager currently mixes management-scope resolution, directory guard checks, dataset
mutation orchestration, and permission-group scope validation. The frontend page hook mixes tree
loading, dataset detail loading, breadcrumb navigation, drag-and-drop moves, create-dialog state,
and directory mutation flows, while the page file still renders the full shell in one place.

That makes small changes to knowledge-base directory management risky because one edit can touch
permissions, dataset movement, selection state, and page rendering at once.

## In Scope

- backend knowledge-management decomposition
- frontend knowledge-bases page and hook decomposition
- focused backend and frontend regression tests

## Out Of Scope

- upload approval or document preview flows
- backend API path or envelope changes
- route-navigation or permission-model changes
- visual redesign of the knowledge-bases page
- new fallback behavior

## Refactor Direction

1. Keep `KnowledgeManagementManager` as the stable backend facade, but extract scope resolution and
   dataset/directory mutation helpers into bounded modules.
2. Keep `KnowledgeBases` as the stable page entry and `useKnowledgeBasesPage` as the stable page
   facade, but split tree/navigation state and knowledge-base action flows into focused hooks.
3. Extract page sections from `KnowledgeBases.js` so the page shell stops owning toolbar, table,
   detail form, and tree panel markup in one file.
4. Preserve current route contracts, page test ids, permission gating, drag-and-drop behavior, and
   knowledge-base create/update/delete flows.

## Acceptance Criteria

1. Backend knowledge-management logic is no longer concentrated in the current manager alone.
2. Frontend knowledge-bases page and hook are no longer single-file owners of all page state and
   rendering concerns.
3. Focused backend and frontend knowledge-management tests pass after the refactor.

## Validation

- `python -m pytest backend/tests/test_knowledge_management_manager_unit.py backend/tests/test_knowledge_directory_route_permissions_unit.py`
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.test.js src/pages/KnowledgeBases.test.js`
