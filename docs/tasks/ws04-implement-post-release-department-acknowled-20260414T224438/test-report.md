# Test Report

- Task ID: `ws04-implement-post-release-department-acknowled-20260414T224438`
- Created: `2026-04-14T22:44:38`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `WS04: Implement post-release department acknowledgment & execution confirmation for document control (see docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws04-department-ack-and-execution-confirmation.md and ws04-department-ack-and-execution-confirmation.md).`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: `python`, `pytest`
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Record the tester's first-pass visibility honestly. In `blind-first-pass`, the tester should record `yes` only after writing an initial verdict before inspecting withheld artifacts.

## Results

### T1: Release creates department acks + inbox notifications

- Result: passed
- Covers: P1-AC1, P2-AC1, P3-AC1, P4-AC1
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: temporary sqlite auth db created via `ensure_schema(...)` in `backend/tests/test_document_control_api_unit.py`
- Evidence refs: `backend/tests/test_document_control_api_unit.py`
- Notes: publish creates two pending ack rows and visible `/api/inbox` `in_app` notifications for department recipients.

### T2: Missing target departments fails fast

- Result: passed
- Covers: P1-AC2
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: same temp sqlite runtime as T1
- Evidence refs: `backend/tests/test_document_control_api_unit.py`
- Notes: publish without configured distribution departments returns `document_control_distribution_departments_missing` and does not silently default departments.

### T3: Department confirmation enforces ownership and is idempotent

- Result: passed
- Covers: P2-AC2
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: same temp sqlite runtime as T1
- Evidence refs: `backend/tests/test_document_control_api_unit.py`
- Notes: matching department confirms successfully, mismatched department gets `403`, and repeated confirm updates the same record.

### T4: Reminder marks overdue and notifies

- Result: passed
- Covers: P3-AC2
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: same temp sqlite runtime as T1
- Evidence refs: `backend/tests/test_document_control_api_unit.py`
- Notes: overdue reminder marks both rows `overdue` and creates visible `/api/inbox` reminder notifications.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P2-AC1, P2-AC2, P3-AC1, P3-AC2, P4-AC1
- Blocking prerequisites:
- Summary: WS04 backend flow is implemented and the targeted unit suite passes with `9 passed`.

## Open Issues

- None yet.
