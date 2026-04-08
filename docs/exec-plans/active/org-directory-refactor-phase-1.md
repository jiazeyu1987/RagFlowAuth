# Org Directory Refactor Phase 1

## Context

The next bounded refactor hotspot after the completed training-compliance tranche is org directory.

Current hotspots:

- `backend/services/org_directory/rebuild_repository.py` concentrates rebuild persistence,
  stale-entity cleanup, and audit logging in one backend file.
- `backend/services/org_directory/manager.py` mixes tree projection with facade responsibilities.
- `fronted/src/pages/OrgDirectoryManagement.js` mixes page shell, tree rendering, search results,
  overview widgets, rebuild controls, and audit panel markup in one page file.
- `fronted/src/features/orgDirectory/useOrgDirectoryManagementPage.js` owns broad page
  orchestration across loading, search, tree state, rebuild flow, and audit refresh logic.

The module already has focused backend and frontend tests, which makes it a good candidate for a
bounded, behavior-preserving refactor.

## In Scope

- backend org-directory rebuild and tree logic decomposition
- frontend org-directory page and hook decomposition
- focused backend/frontend regression tests

## Out Of Scope

- changing API paths or response envelopes
- changing rebuild semantics or Excel parsing rules
- redesigning the org-directory UI
- changing notification behavior outside the existing DingTalk recipient-map rebuild call

## Refactor Direction

1. Keep `OrgStructureManager` as the stable backend facade, but extract tree projection and rebuild
   persistence helpers into bounded modules.
2. Keep `OrgDirectoryManagement` as the stable page entry, but extract tree/search/rebuild/audit
   rendering into focused components and helpers.
3. Extract focused hook logic for search state and rebuild orchestration out of
   `useOrgDirectoryManagementPage`.
4. Preserve all current test ids, rebuild flows, router semantics, and fail-fast behavior.

## Acceptance Criteria

1. Backend org-directory logic is no longer concentrated in the current manager/rebuild pair.
2. Frontend page and hook are no longer single-file owners of all org-directory rendering and page
   orchestration behavior.
3. Focused backend and frontend org-directory tests pass after the refactor.

## Validation

- `python -m pytest backend/tests/test_org_directory_api_unit.py backend/tests/test_org_structure_manager_unit.py`
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/orgDirectory/useOrgDirectoryManagementPage.test.js src/pages/OrgDirectoryManagement.test.js`
