# Electronic Signature Management Page Refactor PRD

- Task ID: `tranche-fronted-src-pages-electronicsignatureman-20260408T082008`
- Created: `2026-04-08T08:20:08`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/pages/ElectronicSignatureManagement.js锛屾媶鍒嗘爣棰樻爣绛惧尯銆佺瓫閫夐潰鏉裤€佺鍚嶅垪琛ㄣ€佺鍚嶈鎯呭拰绛惧悕鎺堟潈鍒楄〃绛夋覆鏌撳尯鍧楋紝淇濇寔 useElectronicSignatureManagementPage 濂戠害涓庣幇鏈?Jest 娴嬭瘯琛屼负绋冲畾`

## Goal

Decompose `ElectronicSignatureManagement.js` so the page header and tabs, filter form, signature
list, signature detail panel, and authorization list stop living in one 526-line route page, while
preserving the existing `useElectronicSignatureManagementPage` contract and current verification and
authorization flows.

## Scope

- `fronted/src/pages/ElectronicSignatureManagement.js`
- new bounded component/helper module(s) under `fronted/src/features/electronicSignature/`
- focused frontend tests:
  - `fronted/src/features/electronicSignature/useElectronicSignatureManagementPage.test.js`
  - `fronted/src/pages/ElectronicSignatureManagement.test.js`
- task artifacts under
  `docs/tasks/tranche-fronted-src-pages-electronicsignatureman-20260408T082008/`

## Non-Goals

- changing electronic signature API payloads, filter semantics, or verification behavior
- redesigning copy, tabs, or page-level permissions
- refactoring `useElectronicSignatureManagementPage.js` unless a tiny compatibility change is
  required for safe extraction
- touching unrelated approval or knowledge pages

## Preconditions

- `fronted/` can run focused Jest tests with `npm test`
- `useElectronicSignatureManagementPage` remains the stable page-facing state and action contract
- existing electronic-signature hook/page Jest suites remain the source of truth for current
  behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- page header, tab switching, and shared status messaging
- signature filter form and total-count display
- signature list and verify action wiring
- signature detail panel rendering
- authorization list rendering and enable/disable action wiring
- page and hook Jest coverage for electronic signature management

## Phase Plan

### P1: Split the electronic signature page into focused render components

- Objective: Move major page render sections into bounded feature components while keeping
  `ElectronicSignatureManagement.js` as the composition page and preserving
  `useElectronicSignatureManagementPage` as the state owner.
- Owned paths:
  - `fronted/src/pages/ElectronicSignatureManagement.js`
  - new component/helper module(s) under `fronted/src/features/electronicSignature/`
  - focused Jest tests listed above as needed
- Dependencies:
  - existing `useElectronicSignatureManagementPage` contract
  - current page text, formatter logic, and tab behavior
- Deliverables:
  - slimmer page composition layer
  - extracted render components for the main UI sections
  - unchanged verification and authorization actions

### P2: Focused frontend regression validation and task evidence

- Objective: Prove the bounded page refactor preserved current electronic-signature hook and page
  behavior.
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

- P1-AC1: `ElectronicSignatureManagement.js` no longer directly owns the page title/tab area,
  signature filter form, signature list table, signature detail panel, and authorization table
  markup in one file.
- P1-AC2: the page continues to consume the same `useElectronicSignatureManagementPage` state/action
  contract without page-level behavior changes.
- P1-AC3: signature verification and authorization toggling continue surfacing the existing loading,
  success, and error states instead of introducing fallback paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused electronic-signature Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `ElectronicSignatureManagement.js` remains the stable route page consuming
  `useElectronicSignatureManagementPage`.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the `useElectronicSignatureManagementPage`
  contract or electronic signature API expectations
- page extraction would require fallback behavior for missing signature data or authorization state
