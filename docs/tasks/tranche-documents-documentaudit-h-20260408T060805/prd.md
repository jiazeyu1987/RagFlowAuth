# Documents / Document Audit Refactor PRD

- Task ID: `tranche-documents-documentaudit-h-20260408T060805`
- Created: `2026-04-08T06:08:18`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勶細浠ヤ笅涓€ tranche 鑱氱劍 documents/document audit 妯″潡锛屾媶鍒嗗悗绔?DocumentManager 涓庡墠绔?DocumentAudit 椤甸潰鍜?hook锛屼繚鎸佺粺涓€鏂囨。涓嬭浇/鍒犻櫎/鎵归噺涓嬭浇涓庡璁￠〉闈㈣涓虹ǔ瀹氬苟琛ラ綈楠岃瘉銆俙`

## Goal

Decompose the current document-management backend facade and document-audit frontend page into
smaller, reviewable units so that preview/download/delete/watermark behavior and audit-page
evolution stop accumulating inside two oversized files, while preserving the existing unified
document route contract and audit UI behavior.

## Scope

- `backend/services/documents/document_manager.py`
- new bounded backend helper modules under `backend/services/documents/`
- `backend/services/documents/__init__.py`
- `backend/app/modules/documents/router.py` only if wiring cleanup is required
- `backend/tests/test_documents_unified_router_unit.py`
- `fronted/src/features/audit/useDocumentAuditPage.js`
- `fronted/src/pages/DocumentAudit.js`
- new bounded frontend helper hooks/components under `fronted/src/features/audit/`
- `fronted/src/features/audit/useDocumentAuditPage.test.js`
- `fronted/src/pages/DocumentAudit.test.js`
- `docs/exec-plans/active/documents-document-audit-refactor-phase-1.md`

## Non-Goals

- changing unified documents API paths or response envelopes
- changing watermark policy semantics or controlled-distribution file contents
- redesigning the document-audit page
- changing knowledge upload approval flows outside the current unified document surface
- broad cleanup of unrelated audit, knowledge, or ragflow routes

## Preconditions

- backend unified document router tests can run locally
- frontend document-audit hook and page tests can run locally
- `DocumentManager` remains the stable backend entry point used by unified document routes
- `DocumentAudit` remains the stable frontend page entry used by routing

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- backend document preview/download/delete/batch-download orchestration and watermark packaging
- unified documents router behavior exercised through `backend/tests/test_documents_unified_router_unit.py`
- frontend document-audit page shell, audit filters, document/deletion/download tabs, and versions modal
- focused tests:
  - `backend/tests/test_documents_unified_router_unit.py`
  - `fronted/src/features/audit/useDocumentAuditPage.test.js`
  - `fronted/src/pages/DocumentAudit.test.js`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: Decompose backend document manager orchestration

- Objective: Split preview/download/delete support responsibilities out of the current backend
  manager while keeping `DocumentManager` as the stable facade used by unified routes.
- Owned paths:
  - `backend/services/documents/document_manager.py`
  - new helper modules under `backend/services/documents/`
  - `backend/services/documents/__init__.py`
  - `backend/app/modules/documents/router.py` only if wiring cleanup is required
- Dependencies:
  - existing unified documents router contract
  - existing document source adapters and watermark service
- Deliverables:
  - slimmer `DocumentManager` facade
  - extracted helper modules for preview/download/delete support
  - unchanged unified download/delete/batch-download behavior

### P2: Decompose frontend document-audit page and hook

- Objective: Split the document-audit page shell and hook into smaller units for data loading,
  filter state, tab rendering, and versions-modal rendering without changing current behavior.
- Owned paths:
  - `fronted/src/features/audit/useDocumentAuditPage.js`
  - `fronted/src/pages/DocumentAudit.js`
  - new helper modules/components under `fronted/src/features/audit/`
- Dependencies:
  - existing `auditApi`
  - existing `usersApi`
  - current page tests and route usage
- Deliverables:
  - slimmer audit page hook
  - extracted audit data/modal helpers
  - extracted page sections that preserve current test ids and interactions

### P3: Focused regression validation and task evidence

- Objective: Prove the bounded documents/document-audit refactor preserved both backend and
  frontend behavior.
- Owned paths:
  - `backend/tests/test_documents_unified_router_unit.py`
  - `fronted/src/features/audit/useDocumentAuditPage.test.js`
  - `fronted/src/pages/DocumentAudit.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused backend/frontend regression coverage
  - execution/test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `DocumentManager` no longer directly owns all preview payload building, watermark
  package construction, unified download response construction, and delete orchestration in one file.
- P1-AC2: existing unified documents router behavior, response envelopes, and controlled download
  semantics remain unchanged.
- P1-AC3: document delete/download flows still fail fast on missing prerequisites, invalid source
  input, and out-of-scope document access.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `useDocumentAuditPage.js` no longer directly owns all data loading, user-name resolution,
  audit filtering, and versions-dialog orchestration in one file.
- P2-AC2: `DocumentAudit.js` no longer mixes page shell, tab switcher, filter controls, table
  renderers, signature-manifest rendering, and versions-modal markup in one file.
- P2-AC3: current page interactions, test ids, version-history loading, and document/deletion/download
  tab behavior remain stable after extraction.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused backend and frontend documents/document-audit tests pass against the final code
  state.
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
- The unified document router contract and document-audit page behavior remain stable.

## Blocking Conditions

- focused backend or frontend validation cannot run
- refactor would require changing public unified document API paths or response envelopes
- preserving current behavior would require fallback branches or silent downgrade
- helper extraction would break controlled-distribution download behavior, delete semantics, or
  document-audit page test contracts
