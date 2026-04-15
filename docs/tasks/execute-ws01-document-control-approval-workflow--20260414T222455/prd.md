# WS01 PRD: Document Control Approval Workflow Contract

- Task ID: `execute-ws01-document-control-approval-workflow--20260414T222455`
- Created: `2026-04-14T22:24:55`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws01-approval-workflow-contract.md 下的工作`

## Goal

Replace the current direct document-control revision status progression with a workflow-driven approval contract (WS01) that:

- uses the existing `backend/services/operation_approval/` engine (request/step/approver model)
- enforces a fixed step sequence: `cosign -> approve -> standardize_review`
- supports reject + restart semantics (reject terminates the approval instance; resubmit creates a new one)
- supports add-sign (adding an approver to the current active step only)
- emits explicit audit events for: submit, step activation, step approval, step rejection, resubmit, add-sign

This task intentionally freezes the backend contract (states, events, endpoints, fail-fast behavior) so downstream workstreams (WS02–WS06) can consume it without redefining approval semantics.

## Scope

- Implement/complete workflow-backed revision actions in `DocumentControlService`:
  - submit for approval
  - approve current step
  - reject current step (terminate instance)
  - add-sign for the current active step
- Replace the document-control API surface so clients can no longer drive direct status transitions.
- Expose revision approval state in the document-control read APIs (revision fields returned to callers).
- Update unit and API tests to assert step order and rejection/restart semantics.

## Non-Goals

- Training workflow and training gate checks (WS02)
- Controlled release / distribution ledger / making revisions `effective` (WS03)
- Department acknowledgment (WS04)
- Obsolete / retention / destruction policy and automation (WS05)
- Frontend workspace redesign and UI wiring (WS06)
- Any fallback path that keeps legacy direct transitions “quietly working”

## Preconditions

These are hard prerequisites for WS01 behavior; missing items must fail fast.

- `ensure_schema()` creates operation-approval tables in the same SQLite database used by document control.
- `deps.user_store.get_by_user_id(user_id)` is available and returns users with `status == "active"` for all approver ids referenced by the workflow.
- `deps.document_control_approval_matrix` is configured (no default/fallback is introduced by WS01). It must map `controlled_documents.document_type` (or `*`) to a list of exactly three steps:
  - step 1: `cosign`
  - step 2: `approve`
  - step 3: `standardize_review`
  - each step defines: `approval_rule` (`all|any`), `member_source` (string), `timeout_reminder_minutes` (int>0), `approver_user_ids` (non-empty list)

If any prerequisite is missing, the API must reject submission explicitly (no legacy transition fallback).

## Impacted Areas

- FastAPI router: `backend/app/modules/document_control/router.py`
- Document control persistence/schema: `backend/database/schema/document_control.py`
- Operation approval engine APIs used by doc-control service: `backend/services/operation_approval/*`
- Tests:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`

## Phase Plan

### P1: Freeze contract types and visibility

- Objective: Expose revision approval state (request id, round, current step) through document-control read APIs so downstream packages can consume a stable contract.
- Owned paths:
  - `backend/services/document_control/models.py`
  - `backend/services/document_control/service.py`
- Dependencies: none
- Deliverables:
  - `ControlledRevision` includes approval-state fields
  - Revision loaders populate those fields from `controlled_revisions`

### P2: Implement workflow-backed actions in `DocumentControlService`

- Objective: Implement submit/approve/reject/resubmit/add-sign semantics using `OperationApprovalStore` + `OperationApprovalDecisionService`, with explicit status gates and audit events.
- Owned paths:
  - `backend/services/document_control/service.py`
  - `backend/services/operation_approval/` (as needed for add-sign primitives/events)
- Dependencies: P1
- Deliverables:
  - `submit_revision_for_approval()` rejects invalid states and missing matrix/user store
  - `approve_revision_approval_step()` advances the workflow, and finalizes to `approved_pending_effective`
  - `reject_revision_approval_step()` terminates the approval instance and sets revision to `approval_rejected`
  - `add_sign_revision_approval_step()` adds an approver to the active step only (no duplicates)
  - Audit events emitted for all required lifecycle points

### P3: Replace API surface (remove direct transitions)

- Objective: Remove the legacy `/transitions` endpoint and replace it with explicit workflow endpoints.
- Owned paths:
  - `backend/app/modules/document_control/router.py`
- Dependencies: P2
- Deliverables:
  - `POST /quality-system/doc-control/revisions/{id}/approval/submit`
  - `POST /quality-system/doc-control/revisions/{id}/approval/approve`
  - `POST /quality-system/doc-control/revisions/{id}/approval/reject`
  - `POST /quality-system/doc-control/revisions/{id}/approval/add-sign`

### P4: Prove step order and rejection semantics with tests

- Objective: Update tests to cover the new contract and ensure the required semantics are enforced.
- Owned paths:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`
- Dependencies: P3
- Deliverables:
  - Unit tests validate: step order, reject terminates instance, resubmit creates new request id/round, add-sign behavior
  - API tests validate the same via FastAPI router

## Phase Acceptance Criteria

### P1

- P1-AC1: `ControlledRevision.as_dict()` includes approval state fields: `approval_request_id`, `approval_last_request_id`, `approval_round`, `approval_submitted_at_ms`, `approval_completed_at_ms`, `current_approval_step_no`, `current_approval_step_name`.
- Evidence expectation: `backend/services/document_control/models.py` and loaders updated; API unit test asserts keys exist.

### P2

- P2-AC1: Submit is fail-fast: missing matrix/user_store or invalid revision status rejects explicitly (no legacy fallback).
- P2-AC2: Approval step order is enforced and fixed (`cosign -> approve -> standardize_review`); final approval moves revision to `approved_pending_effective` and clears `approval_request_id`.
- P2-AC3: Reject terminates the current approval instance and sets revision to `approval_rejected`; resubmit creates a new approval request id and increments `approval_round`.
- P2-AC4: Add-sign adds a new pending approver to the current active step only, disallows duplicates, and does not bypass step completion rules.
- Evidence expectation: service + unit tests cover submit/approve/reject/resubmit/add-sign and audit event emission.

### P3

- P3-AC1: The legacy `/transitions` endpoint is removed (no hidden compatibility path), and the new approval endpoints are available with capability gating.
- Evidence expectation: API unit test calls new endpoints; no route exists for `/transitions`.

### P4

- P4-AC1: The command below passes:

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

- Evidence expectation: `test-report.md` includes command output summary and pass verdict.

## Done Definition

- All phases P1–P4 are completed and recorded with evidence in `execution-log.md` and `test-report.md`.
- New workflow endpoints replace direct revision transitions.
- Required audit event types are emitted for submit, step activation, step approval, step rejection, resubmit, and add-sign.
- No fallback path exists that keeps legacy direct transitions operational.

## Blocking Conditions

- Operation approval engine cannot represent step approvers or add-step-approver behavior (must stop and report exact gap).
- Missing `deps.document_control_approval_matrix` or missing `deps.user_store` for approval resolution (must fail fast at submit time; do not silently downgrade).
