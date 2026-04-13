# WS07 Audit And Evidence Export Test Plan

- Task ID: `ws07-audit-and-evidence-export-md-20260413T234241`
- Created: `2026-04-13T23:42:41`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 WS07-audit-and-evidence-export.md 下的工作（审计事件统一结构、证据导出、搜索/对话留痕）`

## Test Scope

Validate WS07 end-to-end contract at unit/API level:

- unified audit event storage/query model
- search/chat audit trace writes
- evidence export package structure and integrity metadata
- audit log page rendering and export trigger behavior

Out of scope:

- end-user browser E2E for unrelated product domains
- capability model and route registry refactors

## Environment

- OS: Windows (local workspace)
- Python: project backend test runtime
- Node/Jest: frontend test runtime
- Database: temporary sqlite auth.db seeded via tests

## Accounts and Fixtures

- backend tests use seeded admin/viewer fixtures in test modules
- audit evidence fixtures seeded by `_seed_evidence` in export test

Fail fast if Python or Node test runtime is missing.

## Commands

1. `python -m pytest backend/tests/test_audit_events_api_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_search_chat_audit_unit.py -q`
- Expected success signal: all selected backend tests pass.

2. `npm --prefix fronted test -- --watch=false --runInBand src/pages/AuditLogs.test.js src/features/audit/useAuditLogsPage.test.js src/features/audit/api.test.js`
- Expected success signal: all selected frontend audit tests pass.

## Test Cases

### T1: Unified audit event schema and list API

- Covers: P1-AC1, P1-AC2
- Level: backend unit/api
- Command: `python -m pytest backend/tests/test_audit_events_api_unit.py -q`
- Expected: list API returns normalized fields and filters work for WS07 keys.

### T2: Evidence export package integrity and joins

- Covers: P1-AC5
- Level: backend unit/api
- Command: `python -m pytest backend/tests/test_audit_evidence_export_api_unit.py -q`
- Expected: zip package contains manifest/checksums and expected cross-table evidence rows.

### T3: Search/chat trace audit events

- Covers: P1-AC3, P1-AC4
- Level: backend unit
- Command: `python -m pytest backend/tests/test_search_chat_audit_unit.py -q`
- Expected: global search and smart chat produce WS07 action/source/evidence records.

### T4: Audit log UI behavior for WS07 events

- Covers: P1-AC6
- Level: frontend unit
- Command: `npm --prefix fronted test -- --watch=false --runInBand src/pages/AuditLogs.test.js src/features/audit/useAuditLogsPage.test.js src/features/audit/api.test.js`
- Expected: page renders WS07 labels/context/evidence and triggers export action.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | audit api | unified schema/query payload | unit/api | P1-AC1, P1-AC2 | test-report.md#T1 |
| T2 | audit export | evidence package and integrity metadata | unit/api | P1-AC5 | test-report.md#T2 |
| T3 | agents/chat routers | search and chat audit trace writes | unit | P1-AC3, P1-AC4 | test-report.md#T3 |
| T4 | audit frontend | WS07 event render/filter/export interactions | unit | P1-AC6 | test-report.md#T4 |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: pytest, npm, jest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run tests against the actual repository state.
- Escalation rule: do not read withheld artifacts before first verdict is recorded.

## Pass / Fail Criteria

- Pass when all T1-T4 commands succeed and observed results satisfy P1-AC1..P1-AC6.
- Fail when any mapped case fails, or required command cannot run due to missing prerequisite.

## Regression Scope

- `backend/services/audit_log_store.py`
- `backend/services/audit/`
- `backend/app/modules/audit/router.py`
- `backend/app/modules/agents/router.py`
- `backend/app/modules/chat/routes_completions.py`
- `fronted/src/features/audit/`
- `fronted/src/pages/AuditLogs.js`

## Reporting Notes

Write case-by-case outcomes and final verdict to `test-report.md`.
