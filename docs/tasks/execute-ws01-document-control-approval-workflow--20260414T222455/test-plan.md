# WS01 Test Plan: Document Control Approval Workflow Contract

- Task ID: `execute-ws01-document-control-approval-workflow--20260414T222455`
- Created: `2026-04-14T22:24:55`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws01-approval-workflow-contract.md 下的工作`

## Test Scope

Validate WS01 backend workflow contract for document-control revisions:

- fixed step order: `cosign -> approve -> standardize_review`
- submit / approve-step / reject-step / resubmit / add-sign behavior
- explicit fail-fast behavior when prerequisites (matrix, user_store) are missing
- explicit audit events for submit, step activation, step approval, step rejection, resubmit, add-sign
- removal of legacy direct status transition endpoint

Out of scope:

- “make effective / publish / distribution ledger” (WS03)
- training gate enforcement (WS02)
- frontend UI flows (WS06)

## Environment

- Platform: Windows / PowerShell
- Repo: `D:\ProjectPackage\RagflowAuth`
- Runtime: unit tests only (FastAPI TestClient + sqlite temp DB). No server start required.

## Accounts and Fixtures

- No external accounts required.
- Test fixtures must provide:
  - `deps.user_store.get_by_user_id()` for approver resolution
  - `deps.document_control_approval_matrix` describing the 3-step workflow

If any required fixture cannot be provided, the tester must fail fast and record the missing prerequisite.

## Commands

Primary validation command (narrow):

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

Success signal: exit code `0` and all tests pass.

Optional quick sanity checks (not required for pass):

- `rg -n \"approval_in_progress|approval_rejected|approved_pending_effective\" backend/services/document_control/service.py`
  - Success signal: contract state names exist and are used.

## Test Cases

### T1: Approval state fields are visible to callers

- Covers: P1-AC1
- Level: unit + api
- Command: run pytest (primary command)
- Expected: `document["current_revision"]` contains approval-state keys listed in P1-AC1.

### T2: Submit is fail-fast on missing prerequisites and invalid status

- Covers: P2-AC1
- Level: unit
- Command: run pytest
- Expected: submit rejects explicitly when prerequisites or status gates are not satisfied (no fallback).
  - Missing `document_control_approval_matrix` rejects submit explicitly.
  - Missing `user_store` rejects submit explicitly.
  - Submitting from a non-submittable status rejects.

### T3: Fixed step order and final approval semantics

- Covers: P2-AC2
- Level: unit + api
- Command: run pytest
- Expected: approval advances strictly in the required step order and finalizes to `approved_pending_effective`.
  - Step activation/approval advances exactly in the order `cosign -> approve -> standardize_review`.
  - Final approval sets revision status to `approved_pending_effective` and clears `approval_request_id`.

### T4: Reject terminates instance; resubmit restarts with new request id

- Covers: P2-AC3
- Level: unit + api
- Command: run pytest
- Expected: reject ends the approval instance and resubmit creates a new one (new request id/round).
  - Reject moves revision status to `approval_rejected` and clears `approval_request_id`.
  - Resubmit creates a new approval request id and increments `approval_round`.

### T5: Add-sign is constrained to the active step and preserves rules

- Covers: P2-AC4
- Level: unit
- Command: run pytest
- Expected: add-sign is allowed only on the active step and cannot bypass completion rules.
  - Add-sign can only target the current active step.
  - Duplicate approver add-sign is rejected explicitly.
  - The new approver must participate (cannot bypass step completion rule).

### T6: Legacy direct transition endpoint is removed

- Covers: P3-AC1
- Level: api
- Command: run pytest
- Expected: direct transitions are not callable; only the new `/approval/*` endpoints exist.
  - No route exists for `POST /quality-system/doc-control/revisions/{id}/transitions`.
  - New `/approval/*` endpoints exist and work.

### T7: Required validation command passes

- Covers: P4-AC1
- Level: unit + api
- Command: run the primary pytest command in `## Commands`
- Expected: pytest exits with code `0` and all WS01 tests pass.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Document control API | Approval fields present | unit+api | P1-AC1 | `test-report.md#T1` |
| T2 | Service | Submit fail-fast gates | unit | P2-AC1 | `test-report.md#T2` |
| T3 | Service/API | Step order + finalization | unit+api | P2-AC2 | `test-report.md#T3` |
| T4 | Service/API | Reject + resubmit semantics | unit+api | P2-AC3 | `test-report.md#T4` |
| T5 | Service | Add-sign constraints | unit | P2-AC4 | `test-report.md#T5` |
| T6 | Router | `/transitions` removed | api | P3-AC1 | `test-report.md#T6` |
| T7 | Validation | Required pytest command passes | unit+api | P4-AC1 | `test-report.md#T7` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, Python, `pytest`
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo state; do not assume hidden compatibility behavior.
- Escalation rule: If missing prerequisites are discovered, stop and record them rather than inventing a fallback.

## Pass / Fail Criteria

- Pass when:
  - Primary pytest command succeeds.
  - Acceptance ids P1-AC1, P2-AC1..P2-AC4, P3-AC1, P4-AC1 are evidenced in `test-report.md`.
- Fail when:
  - Any legacy `/transitions` behavior remains callable as a compatibility endpoint.
  - Any action silently downgrades on missing matrix/user resolution.
  - Step order is not fixed to `cosign -> approve -> standardize_review`.

## Regression Scope

- `backend/services/operation_approval/*` step/approver semantics
- Document-control read APIs and their JSON payload shape

## Reporting Notes

Record results (commands + key observations) in `test-report.md`.
