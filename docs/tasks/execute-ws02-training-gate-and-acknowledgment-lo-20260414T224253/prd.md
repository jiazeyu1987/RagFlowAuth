# WS02 PRD: Training Gate And Acknowledgment Loop

- Task ID: `execute-ws02-training-gate-and-acknowledgment-lo-20260414T224253`
- Created: `2026-04-14T22:42:53`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Execute WS02: training gate and acknowledgment loop (docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws02-training-gate-and-ack-loop.md)`

## Goal

Turn training from a post-effective side flow into an explicit document-control gate that downstream release/distribution logic (WS03+) can consume.

The WS02 deliverable must provide:

- explicit training gate states for a controlled revision
- explicit blocking behavior when training is required but incomplete
- explicit assignee selection (no implicit default-to-all)
- read-time + acknowledgment controls
- question thread loop that blocks completion until resolved
- auditable records for assignments, questions, resolution, and acknowledgments

## Scope

- Backend training gate + assignments:
  - `backend/services/training_compliance.py`
  - `backend/app/modules/training_compliance/router.py`
  - `backend/database/schema/training_ack.py`
- Minimal document-control integration for status lookup only (no approval semantics changes):
  - `backend/services/document_control/service.py` (read-only assumptions only; avoid redefining approval)
  - `backend/app/modules/document_control/router.py` (only if needed for read surface; prefer training router)
- Tests:
  - `backend/tests/test_training_compliance_api_unit.py`
  - `backend/tests/test_document_control_api_unit.py`

## Non-Goals

- Approval matrix / add-sign / workflow semantics (WS01)
- Controlled release, distribution ledger, “make effective” execution (WS03)
- Department acknowledgment and execution confirmation (WS04)
- Obsolete/retention/destruction policy (WS05)
- Frontend UI implementation (WS06)
- Any fallback that keeps “effective first, training later” quietly working

## Preconditions

- `ensure_schema()` provisions:
  - `controlled_documents` + `controlled_revisions` tables
  - training tables (`training_assignments`, `quality_question_threads`, and WS02 gate config table)
- Controlled revisions used for WS02 training must exist and be in a trainable state:
  - `approved_pending_effective` (primary)
  - `effective` (supported for existing behavior)
- Department-based assignee resolution requires a stable data source:
  - `users.department_id` must exist and be queryable via `UserStore`
- Notification manager is optional for unit tests but must exist in real runtime:
  - missing `notification_manager` must fail fast (no silent ignore)

## Impacted Areas

- Document-control lifecycle consumers:
  - WS03 release/distribution will consume WS02 gate status and blocking behavior
- Training compliance API consumers:
  - assignment generation/configuration UI
  - assignee acknowledgment UI
  - question resolution/reviewer UI
- SQLite schema migrations via `backend/database/schema/ensure.py`
- Unit/API tests listed above

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: Add revision training-gate contract (schema + service)

- Objective: Define a stable, explicit gate contract for a controlled revision that returns one of the required states and a `blocking` signal.
- Owned paths:
  - `backend/database/schema/training_ack.py`
  - `backend/services/training_compliance.py`
  - `backend/app/modules/training_compliance/router.py`
- Dependencies: none
- Deliverables:
  - Schema: a revision-level gate config record (supports `training_required: true|false`)
  - Service: `get_revision_training_gate()` (or equivalent) that returns:
    - `training_required` boolean
    - `gate_status` (explicit states)
    - counts and `blocking` boolean
  - Router: a read endpoint for the gate status

### P2: Make assignment generation explicit and revision-state-aware

- Objective: Remove implicit default-to-all assignee generation and allow explicit selection (users or department).
- Owned paths:
  - `backend/services/training_compliance.py`
  - `backend/app/modules/training_compliance/router.py`
- Dependencies: P1
- Deliverables:
  - Assignment generation supports `approved_pending_effective` revisions (not only `effective`)
  - API rejects generation without explicit assignee selection
  - API supports department-based selection (or fails fast when unavailable)

### P3: Fix question-thread close -> re-ack loop

- Objective: Ensure “question -> resolve -> re-acknowledge” works and open questions block gate completion.
- Owned paths:
  - `backend/services/training_compliance.py`
  - `backend/app/modules/training_compliance/router.py`
  - `backend/database/schema/training_ack.py`
- Dependencies: P2
- Deliverables:
  - Question resolution resets the assignment into an ack-eligible state
  - Gate status reports `questions_open` (or equivalent) when unresolved questions exist

### P4: Prove gate states and blocking with tests

- Objective: Update/add tests to prove WS02 gate state contract and no-default assignment behavior.
- Owned paths:
  - `backend/tests/test_training_compliance_api_unit.py`
  - `backend/tests/test_document_control_api_unit.py`
- Dependencies: P3
- Deliverables:
  - New/updated tests cover: explicit assignee requirement, department selection, gate status transitions, question loop.
  - Validation command passes.

## Phase Acceptance Criteria

List criteria under the matching phase id. Every criterion must use a stable acceptance id.

### P1

- P1-AC1: A revision gate config exists in schema and is ensured by `ensure_schema()` (no manual migrations required).
- P1-AC2: Gate status API returns explicit states at least: `not_required`, `pending_assignment`, `in_progress`, `completed`, `questions_open` (names may differ but semantics must match).
- P1-AC3: Gate status response includes `training_required` and `blocking` fields with deterministic meaning.
- Evidence expectation: schema + service + API unit tests demonstrate the contract.

### P2

- P2-AC1: Assignment generation supports revisions in `approved_pending_effective` and `effective`, and rejects other revision statuses (fail fast).
- P2-AC2: Assignment generation requires explicit assignees; omitting both explicit users and department selection is rejected (no implicit “all active users”).
- P2-AC3: Department-based selection uses a stable data source (`users.department_id`) or fails fast with an explicit error.
- Evidence expectation: API tests cover success + failure cases.

### P3

- P3-AC1: Raising a question creates an open thread and blocks gate completion until resolved.
- P3-AC2: Resolving a question thread resets the assignment so the assignee can acknowledge again (no dead-end `resolved` state).
- Evidence expectation: API tests cover questioned -> resolved -> acknowledged flow.

### P4

- P4-AC1: This command passes:

```powershell
python -m pytest `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

- Evidence expectation: `test-report.md` records the command and pass verdict.

## Done Definition

- Gate contract is implemented and exposed via API.
- No implicit default-to-all assignment behavior remains.
- Question thread loop is not a dead-end; re-ack works after resolution.
- Validation command passes and evidence is recorded.

## Blocking Conditions

- Department-based assignee resolution is requested by the contract but lacks a stable data source.
- Business rule “training blocks release when training_required=true” is contradicted by local requirements (must stop and report).
- Any attempt to keep the old “effective first, training later” behavior as a hidden fallback.
