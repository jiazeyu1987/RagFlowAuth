# Download Controller Refactor PRD

- Task ID: `tranche-fronted-src-features-download-usedownloa-20260408T074226`
- Created: `2026-04-08T07:42:26`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：本 tranche 聚焦 fronted/src/features/download/useDownloadPageController.js，拆分配置持久化、当前下载会话动作、历史面板动作，保持 paper/patent 下载页行为与测试契约稳定`

## Goal

Decompose `useDownloadPageController` into smaller frontend units so download configuration
persistence, current-session orchestration, and history-panel mutations stop accumulating in a
single 500+ line hook, while preserving the paper and patent download page contracts.

## Scope

- `fronted/src/features/download/useDownloadPageController.js`
- new bounded helper hooks or utilities under `fronted/src/features/download/`
- `fronted/src/features/paperDownload/usePaperDownloadPage.js` only if controller wiring cleanup is
  needed
- `fronted/src/features/patentDownload/usePatentDownloadPage.js` only if controller wiring cleanup
  is needed
- focused frontend tests:
  - `fronted/src/features/download/useDownloadPageController.test.js`
  - `fronted/src/features/paperDownload/usePaperDownloadPage.test.js`
  - `fronted/src/features/patentDownload/usePatentDownloadPage.test.js`
  - `fronted/src/pages/PaperDownload.test.js`
  - `fronted/src/pages/PatentDownload.test.js`
- task artifacts under
  `docs/tasks/tranche-fronted-src-features-download-usedownloa-20260408T074226/`

## Non-Goals

- changing paper/patent download API calls or response shapes
- redesigning page layout, copy, or test ids
- introducing real-browser-only behavior changes
- refactoring unrelated `downloadPageUtils`, `useDownloadHistory`, or `useDownloadSessionPolling`
  logic beyond wiring adjustments
- changing permission or routing behavior in the page-level wrappers

## Preconditions

- Node.js/npm test tooling is available.
- Existing Jest-based download controller and page tests can run.
- `useDownloadPageController` remains the stable shared hook used by both paper and patent pages.
- Existing `useDownloadHistory` and `useDownloadSessionPolling` hooks remain available for reuse.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- localStorage-backed configuration hydration and persistence
- current download session polling, stop flow, preview opening, and single/bulk item actions
- history keyword deletion, bulk add, refresh, and selection refresh behavior
- shared controller contract consumed by `usePaperDownloadPage` and `usePatentDownloadPage`
- page-level tests that rely on the controller contract staying stable

## Phase Plan

### P1: Split the shared download controller into focused frontend units

- Objective: Move configuration persistence, current-session actions, and history-panel actions into
  focused helpers while keeping the controller return contract stable.
- Owned paths:
  - `fronted/src/features/download/useDownloadPageController.js`
  - new helper hooks/utilities under `fronted/src/features/download/`
  - page-level wrapper hooks only if adapter cleanup is required
- Dependencies:
  - existing `useDownloadHistory` and `useDownloadSessionPolling`
  - current paper/patent page consumers
  - stable controller return shape used in current tests
- Deliverables:
  - slimmer shared controller
  - extracted helper hooks/utilities for config and action responsibilities
  - unchanged controller contract for page consumers

### P2: Focused frontend regression validation and task evidence

- Objective: Prove the bounded controller refactor preserved current page and hook behavior.
- Owned paths:
  - `fronted/src/features/download/useDownloadPageController.test.js`
  - `fronted/src/features/paperDownload/usePaperDownloadPage.test.js`
  - `fronted/src/features/patentDownload/usePatentDownloadPage.test.js`
  - `fronted/src/pages/PaperDownload.test.js`
  - `fronted/src/pages/PatentDownload.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - focused frontend regression coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `useDownloadPageController.js` no longer directly owns configuration persistence,
  current-session action orchestration, and history-panel mutations in one hook body.
- P1-AC2: paper/patent page wrappers continue to consume the same controller-facing contract without
  page-level behavior changes.
- P1-AC3: download controller failures still surface through the existing error/info channels
  instead of introducing silent downgrade paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused frontend download controller and page tests pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- The shared download controller contract remains stable for both paper and patent page wrappers.

## Blocking Conditions

- focused frontend validation cannot run
- the refactor would require changing controller return fields, page test ids, or download API
  shapes
- preserving current behavior would require fallback branches or silent downgrades
- helper extraction would break the shared controller contract used by the paper/patent wrappers
