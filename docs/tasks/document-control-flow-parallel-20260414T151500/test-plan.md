# Document Control Flow Integration Test Plan

- Task ID: `document-control-flow-parallel-20260414T151500`
- Created: `2026-04-14T20:50:21`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `把文件控制流程初稿与当前系统差异，细化成可由不同 LLM 并行执行的独立工作文件`

## Test Scope

Validate that the integrated implementation now matches the intended PDF workflow across:

- workflow-driven approval instead of direct status transitions
- revision-level training gate before publish
- explicit publish and release ledger behavior
- department acknowledgment and reminder flow
- obsolete, retention, and destruction confirmation flow
- frontend workspace wiring to real document-control APIs

Out of scope:

- unrelated quality-system modules
- real-browser E2E beyond the document-control workspace tests already present

## Environment

- Platform: Windows / PowerShell
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Backend validation: `pytest`
- Frontend validation: `react-scripts test`

## Accounts and Fixtures

- Backend tests use local SQLite fixtures and seeded users.
- Frontend tests use mocked API fixtures.
- Document-control approval runtime requires a configured operation-approval workflow for `document_control_revision_approval`, or a test fixture that injects the workflow contract.

## Commands

- Backend:

```powershell
python -m pytest `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py `
  backend/tests/test_retired_document_access_unit.py -q
```

  - Success signal: exit code 0 and all tests pass

- Frontend:

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js api.test.js userFacingErrorMessages.test.js
```

  - Success signal: exit code 0 and all suites pass

## Test Cases

### T1: Approval workflow replaces direct transitions

- Covers: P1-AC1, P1-AC2
- Level: backend-unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Expected: revisions move through submit -> cosign -> approve -> standardize_review -> approved_pending_effective; reject/resubmit semantics are explicit; add-sign is auditable.

### T2: Training gate blocks publish until satisfied

- Covers: P2-AC1, P2-AC2
- Level: backend-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py backend/tests/test_document_control_service_unit.py -q`
- Expected: trainable revisions support explicit assignment generation, open questions block completion, resolve reopens acknowledgment, and publish is blocked when the gate reports blocking.

### T3: Publish and release ledger are explicit

- Covers: P3-AC1, P3-AC2
- Level: backend-unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Expected: publish uses explicit endpoint/behavior, fails fast when distribution departments are missing, and records release/supersede ledger entries.

### T4: Department acknowledgment uses document-control APIs

- Covers: P4-AC1, P4-AC2
- Level: backend-unit
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: department acks are created after publish, confirmed through document-control endpoints, and overdue reminders stay in the document-control notification path.

### T5: Obsolete, retention, and destruction remain controlled

- Covers: P5-AC1, P5-AC2
- Level: backend-unit
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py backend/tests/test_retired_document_access_unit.py -q`
- Expected: obsolete initiation/approval is explicit, retention access is controlled, and destruction confirmation keeps the offline-disposal boundary explicit.

### T6: Frontend workspace uses real document-control APIs

- Covers: P6-AC1, P6-AC2
- Level: frontend-unit
- Command: `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js api.test.js userFacingErrorMessages.test.js`
- Expected: no direct `Move to ...` buttons remain; frontend uses publish / distribution / department-ack / obsolete APIs and maps new fail-fast errors to user-facing copy.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Approval workflow | workflow-driven approval and reject/resubmit semantics | backend-unit | P1-AC1, P1-AC2 | `test-report.md#T1` |
| T2 | Training gate | gate config, explicit assignees, question loop, publish blocking | backend-unit | P2-AC1, P2-AC2 | `test-report.md#T2` |
| T3 | Publish | explicit publish and release ledger | backend-unit | P3-AC1, P3-AC2 | `test-report.md#T3` |
| T4 | Department acknowledgment | ack creation, confirmation, reminder path | backend-unit | P4-AC1, P4-AC2 | `test-report.md#T4` |
| T5 | Obsolete lifecycle | obsolete, retention, destruction boundary | backend-unit | P5-AC1, P5-AC2 | `test-report.md#T5` |
| T6 | Frontend workspace | real document-control API wiring | frontend-unit | P6-AC1, P6-AC2 | `test-report.md#T6` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, python, pytest, react-scripts
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: validate against the real repo state and real test/runtime commands, not chat summaries.
- Escalation rule: if any required workflow prerequisite is missing, fail fast and record the exact blocker.

## Pass / Fail Criteria

- Pass when:
  - T1 through T6 all pass
  - every PRD acceptance id is covered by at least one passing test case
- Fail when:
  - any command fails
  - publish still bypasses revision-level training gate
  - frontend still proxies change-control data instead of using document-control APIs

## Regression Scope

- `backend/services/operation_approval/`
- `backend/services/training_compliance.py`
- `backend/services/document_control/`
- `fronted/src/features/documentControl/`
- `fronted/src/pages/DocumentControl.js`

## Reporting Notes

Record results in `test-report.md` using T1 through T6 headings.
