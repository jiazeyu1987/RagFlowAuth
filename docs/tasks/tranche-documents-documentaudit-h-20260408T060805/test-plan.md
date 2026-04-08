# Documents / Document Audit Refactor Test Plan

- Task ID: `tranche-documents-documentaudit-h-20260408T060805`
- Created: `2026-04-08T06:08:18`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勶細浠ヤ笅涓€ tranche 鑱氱劍 documents/document audit 妯″潡锛屾媶鍒嗗悗绔?DocumentManager 涓庡墠绔?DocumentAudit 椤甸潰鍜?hook锛屼繚鎸佺粺涓€鏂囨。涓嬭浇/鍒犻櫎/鎵归噺涓嬭浇涓庡璁￠〉闈㈣涓虹ǔ瀹氬苟琛ラ綈楠岃瘉銆俙`

## Test Scope

Validate that the bounded documents/document-audit refactor preserves:

- backend unified document download, delete, upload-request, and batch-download route behavior
- frontend document-audit page loading, filter derivation, version-history modal loading, and tab rendering

Out of scope:

- broader knowledge upload approval flows beyond the unified documents router contract
- visual redesign or accessibility restyling checks
- unrelated ragflow or audit export regressions outside the targeted document surface

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python pytest / unittest-compatible environment already used by repo tests
- Frontend: Node.js/npm with Jest via `react-scripts test`

## Accounts and Fixtures

- backend tests rely on temporary files, mocked document stores, mocked ragflow service, and FastAPI test client wiring
- frontend tests rely on mocked `useAuth`, mocked `auditApi`, and mocked `usersApi`
- if either Python or npm tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_documents_unified_router_unit.py`
  - Expected success signal: focused unified document backend suite passes
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/audit/useDocumentAuditPage.test.js src/pages/DocumentAudit.test.js`
  - Expected success signal: focused document-audit frontend suites pass

## Test Cases

### T1: Backend unified documents contract regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / route integration
- Command: `python -m pytest backend/tests/test_documents_unified_router_unit.py`
- Expected: unified download/delete/upload-request/batch-download route behavior and response contracts remain stable

### T2: Frontend document-audit page regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/audit/useDocumentAuditPage.test.js src/pages/DocumentAudit.test.js`
- Expected: audit lists, filters, display-name resolution, and version-history dialog behavior remain stable

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | unified documents backend | document manager decomposition preserves unified route behavior and fail-fast semantics | unit/route integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | document audit frontend | page/hook decomposition preserves audit interactions and modal loading behavior | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. If a UI or interaction path is in scope, use a real browser or session and record concrete evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - backend unified document behavior and frontend document-audit interactions remain stable
- Fail when:
  - either focused test command fails
  - controlled download/delete behavior, response envelopes, or document-audit interactions regress

## Regression Scope

- `backend/services/documents/*`
- `backend/app/modules/documents/router.py`
- `backend/tests/test_documents_unified_router_unit.py`
- `fronted/src/features/audit/*`
- `fronted/src/pages/DocumentAudit.js`
- `fronted/src/pages/DocumentAudit.test.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each suite passed.
