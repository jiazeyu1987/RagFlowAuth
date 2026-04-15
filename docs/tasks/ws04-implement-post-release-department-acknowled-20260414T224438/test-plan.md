# WS04 Department Ack (Test Plan)

- Task ID: `ws04-implement-post-release-department-acknowled-20260414T224438`
- Created: `2026-04-14T22:44:38`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Validation target (from WS04 prompt): `python -m pytest backend/tests/test_document_control_api_unit.py -q`

## Test Scope

Validate backend behavior for Document Control department acknowledgments:

- Effective transition creates per-department ack records (`pending`) and emits in-app inbox notifications.
- Department confirmation updates ack state (`confirmed`) with audit fields and enforces department ownership.
- Reminder action marks overdue items (`overdue`) and emits reminder inbox notifications.
- Fail-fast behavior when target departments are missing (no implicit “all departments”).

Out of scope:

- Approval workflow matrix / training gates / release ledger / frontend UI.

## Environment

- Platform: Windows / PowerShell
- Repo: `D:\ProjectPackage\RagflowAuth`
- Runtime: Unit tests only (FastAPI TestClient + sqlite temp db)
- Required tools: `python`, `pytest`

## Accounts and Fixtures

Unit tests must seed:

- A sqlite auth db via `ensure_schema(...)`.
- A notification `in_app` channel (same as runtime default `inapp-main`).
- A minimal set of active users with `department_id` values matching the configured target departments.

If any prerequisite is missing (e.g., cannot create in_app channel, no users for a department), the test must fail fast.

## Commands

- `python -m pytest backend/tests/test_document_control_api_unit.py -q`
  - Success signal: exit code `0`

## Test Cases

### T1: Release creates department acks + inbox notifications

- Covers: P1-AC1, P2-AC1, P3-AC1, P4-AC1
- Level: unit/api
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: After transitioning a revision to `effective`, ack rows exist for each configured department with `pending` status and in-app inbox items exist for users in those departments.

### T2: Missing target departments fails fast

- Covers: P1-AC2
- Level: unit/api
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: Transition to `effective` fails with a clear error when no target departments are configured for the document.

### T3: Department confirmation enforces ownership and is idempotent

- Covers: P2-AC2
- Level: unit/api
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: Matching-department user can confirm and record `confirmed_by/confirmed_at/notes`; mismatched department is rejected (unless admin); repeat confirm updates the same row without duplication.

### T4: Reminder marks overdue and notifies

- Covers: P3-AC2
- Level: unit/api
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: Pending acks past due are marked `overdue` and the reminder action creates in-app inbox items for the department recipients.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | doc-control | effective -> ack + inbox | unit/api | P1-AC1, P2-AC1, P3-AC1 | `test-report.md#T1` |
| T2 | doc-control | missing departments -> fail-fast | unit/api | P1-AC2 | `test-report.md#T2` |
| T3 | doc-control | confirm ack ownership | unit/api | P2-AC2 | `test-report.md#T3` |
| T4 | doc-control | overdue reminder | unit/api | P3-AC2 | `test-report.md#T4` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: `python`, `pytest`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run unit tests against the real repo code and a temporary sqlite db seeded via `ensure_schema(...)`; do not mock success paths.
- Escalation rule: If department mapping or recipients cannot be resolved in the test environment, fail fast and record the missing prerequisite instead of inventing defaults.

## Pass / Fail Criteria

- Pass when:
  - All tests in `backend/tests/test_document_control_api_unit.py` pass.
  - Evidence is recorded in `test-report.md` for T1–T4.
- Fail when:
  - Any acceptance behavior is missing or replaced with fallback (e.g., defaulting to “all departments”).
  - Any test fails or required prerequisite is missing.

## Regression Scope

- `backend/services/notification/` event catalog seeding and inbox listing behavior.
- Document control effective transition behavior (`DocumentControlService.transition_revision`).

## Reporting Notes

Write results to `test-report.md` with:

- Command(s) run + exit code.
- Assertions/evidence for each test case T1–T4.
