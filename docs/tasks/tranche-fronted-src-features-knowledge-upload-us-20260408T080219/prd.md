# Knowledge Upload Hook Refactor PRD

- Task ID: `tranche-fronted-src-features-knowledge-upload-us-20260408T080219`
- Created: `2026-04-08T08:02:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/features/knowledge/upload/useKnowledgeUploadPage.js锛屾媶鍒嗙煡璇嗗簱鍔犺浇绛涢€夈€佹墿灞曞悕閰嶇疆绠＄悊銆佹枃浠堕€夋嫨涓庝笂浼犳祦绋嬬姸鎬侊紝淇濇寔 KnowledgeUpload 椤甸潰杩斿洖濂戠害涓庣幇鏈?Jest 娴嬭瘯琛屼负绋冲畾`

## Goal

Decompose the mixed-responsibility `useKnowledgeUploadPage` hook so dataset loading and filtering,
allowed-extension settings management, and file-selection/upload orchestration stop living in one
451-line hook body, while preserving the `KnowledgeUpload` page contract and existing fail-fast
behavior.

## Scope

- `fronted/src/features/knowledge/upload/useKnowledgeUploadPage.js`
- new bounded helper module(s) under `fronted/src/features/knowledge/upload/`
- focused frontend tests:
  - `fronted/src/features/knowledge/upload/useKnowledgeUploadPage.test.js`
  - `fronted/src/pages/KnowledgeUpload.test.js`
  - `fronted/src/features/knowledge/upload/api.test.js`
- task artifacts under
  `docs/tasks/tranche-fronted-src-features-knowledge-upload-us-20260408T080219/`

## Non-Goals

- changing `KnowledgeUpload` route paths, page layout, or submitted approval flow
- redesigning upload error copy, permission semantics, or allowed-extension backend payloads
- refactoring unrelated knowledge pages such as `KnowledgeBases.js` or `NasBrowser.js`
- adding fallback behavior when knowledge bases or allowed extensions cannot be loaded

## Preconditions

- `fronted/` can run focused Jest tests with `npm test`
- `useKnowledgeUploadPage` remains the single page-facing hook contract consumed by
  `fronted/src/pages/KnowledgeUpload.js`
- the existing knowledge-upload hook/page/api Jest suites remain the source of truth for current
  behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- knowledge-base loading, directory merge, visibility filtering, and search selection
- allowed-extension fetch/update and admin-only settings flow
- file selection, drag-and-drop, upload progress, and approval redirect behavior
- `KnowledgeUpload` page consumption of the hook return contract
- focused Jest tests for the hook, page, and upload feature API

## Phase Plan

### P1: Split the knowledge upload hook into focused frontend units

- Objective: Extract bounded helper modules for dataset state, extension settings, and upload-file
  actions while keeping `useKnowledgeUploadPage` as the stable composition hook.
- Owned paths:
  - `fronted/src/features/knowledge/upload/useKnowledgeUploadPage.js`
  - new helper module(s) under `fronted/src/features/knowledge/upload/`
  - focused Jest tests listed above as needed
- Dependencies:
  - existing `knowledgeApi`, `knowledgeUploadApi`, and `useAuth` contracts
  - current `KnowledgeUpload` page hook return shape
- Deliverables:
  - slimmer page hook composed from focused helpers
  - stable upload page return contract
  - unchanged fail-fast upload and extension-management behavior

### P2: Focused frontend regression validation and task evidence

- Objective: Prove the bounded upload-hook refactor preserved current hook/page/API behavior.
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

- P1-AC1: `useKnowledgeUploadPage.js` no longer directly owns knowledge-base loading/filtering,
  allowed-extension settings management, and file-selection/upload flow logic in one hook body.
- P1-AC2: `KnowledgeUpload.js` continues to consume the same hook-facing contract without page-level
  behavior changes.
- P1-AC3: missing visible knowledge bases, unavailable allowed extensions, and upload failures still
  fail fast through the existing error and state channels instead of introducing silent downgrade
  paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused knowledge-upload Jest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `useKnowledgeUploadPage` remains the stable page-facing hook contract for `KnowledgeUpload.js`.

## Blocking Conditions

- focused frontend validation cannot run in `fronted/`
- preserving current behavior would require changing the hook return contract, page API, or upload
  feature API payload shape
- helper extraction would require fallback or silent downgrade behavior for missing knowledge bases
  or extension settings
