# WS02 Test Plan: Training Gate And Acknowledgment Loop

- Task ID: `execute-ws02-training-gate-and-acknowledgment-lo-20260414T224253`
- Created: `2026-04-14T22:42:53`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Execute WS02: training gate and acknowledgment loop (docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws02-training-gate-and-ack-loop.md)`

## Test Scope

Validate the WS02 backend contract end-to-end at the API level:

- explicit training gate states for a controlled revision
- explicit blocking behavior when training is required but incomplete
- explicit assignee selection (no implicit default-to-all)
- question thread loop: questioned -> resolved -> re-acknowledged

Out of scope:

- approval workflow semantics (WS01)
- release/distribution (WS03)
- department acknowledgment (WS04)
- frontend UI

## Environment

- Platform: Windows / PowerShell
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Runtime: unit tests only (FastAPI TestClient + SQLite temp db)
- Schema: `backend/database/schema/ensure.py::ensure_schema()` must be executed by tests

## Accounts and Fixtures

- No real accounts required; tests seed users into SQLite.
- Fixtures needed by WS02 tests:
  - a controlled document + controlled revision row with status `approved_pending_effective`
  - at least two active users in the same department to validate department-based selection

## Commands

- `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
  - Success signal: exit code 0
- `python -m pytest backend/tests/test_document_control_api_unit.py -q`
  - Success signal: exit code 0
- Full WS02 validation:

```powershell
python -m pytest `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

  - Success signal: exit code 0, all tests passed

## Test Cases

Use stable test case ids. Every acceptance id from the PRD should appear in at least one `Covers` field.

### T1: Gate status returns explicit state contract

- Covers: P1-AC1, P1-AC2, P1-AC3
- Level: api-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
- Expected: Gate endpoint returns `training_required`, `gate_status`, and `blocking` with stable semantics and explicit state values.

### T2: Assignment generation is explicit (no default-to-all)

- Covers: P2-AC2
- Level: api-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
- Expected: Generating assignments without explicit users/departments fails fast with a deterministic 400-level error.

### T3: Department-based selection creates assignments for active users

- Covers: P2-AC3
- Level: api-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
- Expected: Providing department ids resolves active users and generates assignments; no implicit global broadcast.

### T4: Question loop blocks completion until resolved, then allows re-ack

- Covers: P3-AC1, P3-AC2
- Level: api-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
- Expected: decision=`questioned` opens a thread and blocks completion; resolving resets the assignment to ack-eligible; final decision=`acknowledged` allows the gate to become “completed”.

### T5: Assignment generation supports approved_pending_effective revisions

- Covers: P2-AC1
- Level: api-unit
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py -q`
- Expected: Assignment generation succeeds for `approved_pending_effective` revisions and rejects unsupported statuses.

### T6: Document control API test uses workflow endpoints (no /transitions)

- Covers: P4-AC1
- Level: api-unit
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: Test suite passes against the current workflow-based document-control API surface.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Gate API | Gate status contract | api-unit | P1-AC1, P1-AC2, P1-AC3 | `test-report.md#T1` |
| T2 | Assignments | No default-to-all | api-unit | P2-AC2 | `test-report.md#T2` |
| T3 | Assignments | Department selection | api-unit | P2-AC3 | `test-report.md#T3` |
| T4 | Questions | Question loop + re-ack | api-unit | P3-AC1, P3-AC2 | `test-report.md#T4` |
| T5 | Revisions | approved_pending_effective support | api-unit | P2-AC1 | `test-report.md#T5` |
| T6 | Doc control API | workflow endpoints | api-unit | P4-AC1 | `test-report.md#T6` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, python, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. If a UI or interaction path is in scope, use a real browser or session and record concrete evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - all test cases T1–T6 pass
  - gate states are explicit and blocking behavior is deterministic (no implicit default-to-all)
- Fail when:
  - any test fails
  - any endpoint silently falls back to “assign all active users” behavior
  - unresolved questions do not block completion or the resolve step leaves a dead-end state

## Regression Scope

- `backend/services/training_compliance.py` assignment/ack flows
- `backend/database/schema/ensure.py` schema idempotency
- Notification event plumbing (must fail fast when unavailable)

## Reporting Notes

Write results to `test-report.md` using T1–T6 headings.
