# WS07 Audit And Evidence Export PRD

- Task ID: `ws07-audit-and-evidence-export-md-20260413T234241`
- Created: `2026-04-13T23:42:41`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 WS07-audit-and-evidence-export.md 下的工作（审计事件统一结构、证据导出、搜索/对话留痕）`

## Goal

Deliver WS07 with a single quality-audit event contract and evidence export path that already works in code for:

- unified audit event schema and query model
- global search trace (`global_search_execute`)
- smart chat trace (`smart_chat_completion`)
- downloadable evidence package with integrity metadata and cross-table evidence joins

## Scope

In scope files and flows:

- `backend/database/schema/audit_logs.py`
- `backend/services/audit_log_store.py`
- `backend/services/audit_helpers.py`
- `backend/services/audit/*`
- `backend/app/modules/audit/router.py`
- `backend/app/modules/agents/router.py` (global search audit trace)
- `backend/app/modules/chat/routes_completions.py` (smart chat audit trace)
- `fronted/src/features/audit/*`
- `fronted/src/pages/AuditLogs.js`
- `fronted/src/pages/DocumentAudit.js`
- `fronted/src/pages/Agents.js`
- `fronted/src/pages/Chat.js`
- related unit tests under `backend/tests` and `fronted/src/**/**.test.js`

## Non-Goals

- No ownership takeover of business-domain logic from WS01/WS03/WS04/WS05/WS06/WS08.
- No route or capability renaming in:
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/shared/auth/capabilities.js`
  - `backend/app/core/permission_models.py`
- No fallback branch, mock success path, or silent downgrade for missing audit dependencies.

## Preconditions

- Python test environment can run backend unit tests.
- Node/Jest environment can run frontend unit tests.
- SQLite schema bootstrap (`ensure_schema`) is available in tests.
- Existing WS07 module files are readable in the current workspace.

If any precondition is missing, execution must stop and record in `task-state.json.blocking_prereqs`.

## Impacted Areas

- Audit event table schema fields and indexes.
- Audit manager/list API serialization contract.
- Evidence export zip format (`manifest.json`, `checksums.json`, csv/json payloads).
- Search and chat routers writing unified quality events.
- Audit logs page filter/render/export behavior.
- Unit tests validating WS07 contract.

## Phase Plan

### P1: Verify And Finalize WS07 Delivery

- Objective:
  - Confirm WS07 acceptance is satisfied by current code and tests.
  - Fix code only if tests or acceptance checks expose real gaps.
- Owned paths:
  - `backend/database/schema/audit_logs.py`
  - `backend/services/audit_log_store.py`
  - `backend/services/audit_helpers.py`
  - `backend/services/audit/*`
  - `backend/app/modules/audit/router.py`
  - `backend/app/modules/agents/router.py`
  - `backend/app/modules/chat/routes_completions.py`
  - `backend/tests/test_audit_events_api_unit.py`
  - `backend/tests/test_audit_evidence_export_api_unit.py`
  - `backend/tests/test_search_chat_audit_unit.py`
  - `fronted/src/features/audit/*`
  - `fronted/src/pages/AuditLogs.js`
  - `fronted/src/pages/AuditLogs.test.js`
- Dependencies:
  - Existing WS07 implementation in repository.
  - Local test runtime.
- Deliverables:
  - Verified WS07 behavior evidence in `execution-log.md`.
  - Independent test verdict in `test-report.md`.
  - Completed task state through completion gate.

## Phase Acceptance Criteria

### P1

- P1-AC1: `audit_events` schema supports unified WS07 fields for action/source/resource/event metadata, before/after snapshots, request/signature trace, and evidence references.
- P1-AC2: audit API query supports unified filtering and returns normalized event payloads including decoded `meta` and `evidence_refs`.
- P1-AC3: global search flow writes `global_search_execute` quality audit event with request context and evidence references.
- P1-AC4: smart chat completion flow writes `smart_chat_completion` quality audit event with citation evidence references.
- P1-AC5: evidence export API returns downloadable package containing csv/json record copies and integrity metadata (`manifest.json` + `checksums.json`) with expected evidence counts.
- P1-AC6: frontend audit log page can render/search/export WS07 event classes (including global search and smart chat records).
- Evidence expectation:
  - backend and frontend unit test outputs in `test-report.md`
  - execution notes linked from `execution-log.md#Phase-P1`

## Done Definition

Task is done only when all are true:

- Phase P1 status is `completed`.
- P1-AC1..P1-AC6 are `completed` with evidence refs.
- `test_status` is `passed`.
- `check_completion.py --apply` succeeds.

## Blocking Conditions

- Required test runtimes are unavailable.
- Required WS07 files are unreadable or missing.
- Any acceptance-mapped unit test fails and the failure cannot be resolved in-scope.
- Evidence export contract regression (missing manifest/checksum/integrity fields).
