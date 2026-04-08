# Org Directory Refactor PRD

- Task ID: `tranche-org-directory-orgdirectory-h-20260408T050500`
- Created: `2026-04-08T04:49:24`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勶細浠ヤ笅涓€ tranche 鑱氱劍 org directory 妯″潡锛屾媶鍒嗗悗绔?org_directory rebuild/tree 閫昏緫涓庡墠绔?OrgDirectoryManagement 椤甸潰鍜?hook锛屼繚鎸佽涓虹ǔ瀹氬苟琛ラ綈楠岃瘉銆俙`

## Goal

Decompose the org-directory backend rebuild/tree logic and the frontend org-directory page/hook
into smaller, reviewable units so that future tree rendering, Excel rebuild, audit display, and
DingTalk recipient-map integration changes stop accumulating in two oversized files, while
preserving the current API and UI behavior.

## Scope

- `backend/services/org_directory/manager.py`
- `backend/services/org_directory/rebuild_repository.py`
- `backend/services/org_directory/store.py` only if dependency wiring cleanup is needed
- new bounded backend helper modules under `backend/services/org_directory/`
- `fronted/src/pages/OrgDirectoryManagement.js`
- `fronted/src/features/orgDirectory/useOrgDirectoryManagementPage.js`
- new bounded frontend helper modules/components under `fronted/src/features/orgDirectory/`
- focused backend and frontend org-directory tests
- `docs/exec-plans/active/org-directory-refactor-phase-1.md`

## Non-Goals

- changing org-directory API paths or response envelopes
- changing Excel parsing rules or rebuild business behavior
- redesigning the org-directory UI
- changing notification channel behavior outside the existing DingTalk rebuild call path
- changing unrelated org/user management modules

## Preconditions

- Existing backend org-directory tests can run.
- Existing frontend org-directory page and hook tests can run.
- `OrgStructureManager` remains the stable backend entry point used by router wiring.
- `OrgDirectoryManagement` remains the stable page entry used by routing.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- backend org-directory rebuild persistence, stale cleanup, and tree projection flows
- router-level org-directory API behavior exercised through `test_org_directory_api_unit.py`
- frontend page shell, tree rendering, search panel, overview/audit tabs, and rebuild controls
- frontend hook responsibilities for initial loading, search result derivation, tree state, and
  rebuild orchestration
- notification integration limited to the existing DingTalk recipient-map rebuild call after org
  rebuild success

## Phase Plan

### P1: Decompose backend org-directory rebuild and tree logic

- Objective: Split tree-building and rebuild-persistence responsibilities out of the current
  manager/repository concentration while keeping `OrgStructureManager` as the stable facade.
- Owned paths:
  - `backend/services/org_directory/manager.py`
  - `backend/services/org_directory/rebuild_repository.py`
  - `backend/services/org_directory/store.py` only if wiring cleanup is required
  - new helper modules under `backend/services/org_directory/`
- Dependencies:
  - existing SQLite schema
  - existing org-directory router contract
  - existing Excel parser and rebuild types
- Deliverables:
  - slimmer backend manager/repository entry points
  - extracted helper modules for tree projection and rebuild persistence responsibilities
  - unchanged backend API behavior

### P2: Decompose frontend org-directory page and hook

- Objective: Split the page shell and hook into smaller units for tree rendering, search UI,
  rebuild controls, and page-state orchestration without changing current page behavior.
- Owned paths:
  - `fronted/src/pages/OrgDirectoryManagement.js`
  - `fronted/src/features/orgDirectory/useOrgDirectoryManagementPage.js`
  - new helper modules/components under `fronted/src/features/orgDirectory/`
- Dependencies:
  - existing `orgDirectoryApi`
  - existing `notificationApi` DingTalk rebuild flow
  - current page tests and route usage
- Deliverables:
  - slimmer page component
  - extracted helper hooks/components for tree/search/rebuild sections
  - stable page-level behavior and test ids

### P3: Focused regression validation and task evidence

- Objective: Prove the bounded org-directory refactor preserved both backend and frontend behavior.
- Owned paths:
  - `backend/tests/test_org_directory_api_unit.py`
  - `backend/tests/test_org_structure_manager_unit.py`
  - `fronted/src/features/orgDirectory/useOrgDirectoryManagementPage.test.js`
  - `fronted/src/pages/OrgDirectoryManagement.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused backend/frontend regression coverage
  - execution/test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `OrgStructureManager` and org-directory rebuild persistence no longer directly own all
  tree projection, stale-entity cleanup, and mutation orchestration in one concentrated pair of
  files.
- P1-AC2: existing org-directory router behavior, rebuild summaries, and stable-id rebuild
  semantics remain unchanged.
- P1-AC3: org-directory rebuild/tree logic still fails fast on missing actor, broken relationships,
  and invalid Excel-derived state.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `OrgDirectoryManagement.js` no longer mixes page shell, tab layout, tree rendering,
  search result rendering, selected-person cards, rebuild widgets, and audit panel markup in one
  file.
- P2-AC2: `useOrgDirectoryManagementPage.js` no longer directly owns all search derivation,
  rebuild orchestration, responsive state, and audit loading logic in one file.
- P2-AC3: current page interactions, test ids, rebuild behavior, and overview/audit tab behavior
  remain stable after extraction.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused backend and frontend org-directory tests pass against the final code state.
- P3-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- The org-directory backend facade, API behavior, frontend page contract, and focused user flows
  remain stable.

## Blocking Conditions

- focused backend or frontend validation cannot run
- refactor would require changing public API paths or response envelopes
- preserving current behavior would require fallback branches or silent downgrades
- helper extraction would break Excel rebuild semantics, tree shape, or the existing DingTalk
  rebuild integration
