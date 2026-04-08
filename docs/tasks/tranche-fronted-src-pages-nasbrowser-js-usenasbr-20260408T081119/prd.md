# Nas Browser Page Refactor PRD

- Task ID: `tranche-fronted-src-pages-nasbrowser-js-usenasbr-20260408T081119`
- Created: `2026-04-08T08:11:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/pages/NasBrowser.js锛屾媶鍒嗛〉闈㈠ご閮ㄥ鑸€佽矾寰勯潰鍖呭眿銆佸鍏ヨ繘搴﹂潰鏉裤€佹枃浠跺垪琛ㄨ〃鏍煎拰瀵煎叆瀵硅瘽妗嗙瓑娓叉煋鍖哄潡锛屼繚鎸?useNasBrowserPage 濂戠害銆佽矾鐢辫涓轰笌鐜版湁 Jest 娴嬭瘯绋冲畾`

## Goal

Decompose the 604-line `NasBrowser` page into focused render components for the page header,
breadcrumbs, progress panel, file table, and import dialog, while preserving the existing
`useNasBrowserPage` integration, route behavior, and NAS import UI flow.

## Scope

- `fronted/src/pages/NasBrowser.js`
- new bounded component module(s) under `fronted/src/features/knowledge/nasBrowser/`
- focused frontend tests:
  - `fronted/src/features/knowledge/nasBrowser/useNasBrowserPage.test.js`
  - `fronted/src/pages/NasBrowser.test.js`
- task artifacts under
  `docs/tasks/tranche-fronted-src-pages-nasbrowser-js-usenasbr-20260408T081119/`

## Non-Goals

- changing NAS API payloads, polling semantics, or folder-import business rules
- redesigning page copy, route paths, or admin permissions
- refactoring `useNasBrowserPage.js` unless a small compatibility change is required for safe page
  extraction
- touching unrelated knowledge-upload, knowledge-base, or tools pages

## Preconditions

- `fronted/` can run focused Jest tests with `npm test`
- `useNasBrowserPage` remains the stable page-facing state and action contract
- existing NAS browser hook/page Jest suites remain the source of truth for current behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- NAS browser header and navigation actions
- breadcrumb rendering and parent-directory navigation
- folder import progress panel and skipped/failed detail rendering
- NAS items table row rendering and import button wiring
- import dialog knowledge-base selection and submit/cancel actions
- page and hook Jest coverage for the NAS browser feature

## Phase Plan

### P1: Split the NAS browser page into focused render components

- Objective: Move major page render sections into bounded feature components while keeping
  `NasBrowser.js` as the composition page and preserving `useNasBrowserPage` as the business-state
  owner.
- Owned paths:
  - `fronted/src/pages/NasBrowser.js`
  - new component module(s) under `fronted/src/features/knowledge/nasBrowser/`
  - focused Jest tests listed above as needed
- Dependencies:
  - existing `useNasBrowserPage` contract
  - current NAS browser styles and utility formatters
- Deliverables:
  - slimmer page composition layer
  - extracted render components for high-density UI sections
  - unchanged page-level behavior and import actions

### P2: Focused frontend regression validation and task evidence

- Objective: Prove the bounded page refactor preserved current NAS browser hook and page behavior.
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

- P1-AC1: `NasBrowser.js` no longer directly owns the page header, breadcrumb and parent navigation,
  folder import progress rendering, NAS item table rendering, and import dialog markup in one file.
- P1-AC2: the page continues to consume the same `useNasBrowserPage` state/action contract without
  route-level or import-flow behavior changes.
- P1-AC3: admin gating, import progress rendering, and import dialog actions keep surfacing the
  existing states and errors instead of introducing silent fallback paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused NAS browser Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `NasBrowser.js` remains the stable route page consuming `useNasBrowserPage`.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the `useNasBrowserPage` contract, route path,
  or NAS API expectations
- page extraction would require fallback behavior for missing admin permission, import state, or NAS
  data
