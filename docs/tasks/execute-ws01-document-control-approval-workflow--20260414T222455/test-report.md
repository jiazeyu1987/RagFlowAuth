# Test Report

- Task ID: `execute-ws01-document-control-approval-workflow--20260414T222455`
- Created: `2026-04-14T22:24:55`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Execute WS01: document control approval workflow contract (submit/approve/reject/resubmit/add-sign)`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: python, pytest
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: Approval state fields are visible to callers

- Result: passed
- Covers: P1-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: temp sqlite DB created by `backend/tests/test_document_control_service_unit.py` and `backend/tests/test_document_control_api_unit.py`
- Evidence refs: `backend/services/document_control/models.py`, `backend/services/document_control/service.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: read APIs now expose approval request id, last request id, round, submitted/completed timestamps, and current step fields on revisions.

### T2: Submit is fail-fast on missing prerequisites and invalid status

- Result: passed
- Covers: P2-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: unit test fixture constructs services with and without `document_control_approval_matrix` / `user_store`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: submit rejects missing matrix, missing user store, and invalid revision status without falling back to legacy transitions.

### T3: Fixed step order and final approval semantics

- Result: passed
- Covers: P2-AC2
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: service/API fixtures exercise `cosign`, `approve`, and `standardize_review` with distinct users
- Evidence refs: `backend/tests/test_document_control_service_unit.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: approval advances strictly in the required order and final approval leaves the revision in `approved_pending_effective` with `approval_request_id = None`.

### T4: Reject terminates instance and resubmit creates a new request

- Result: passed
- Covers: P2-AC3
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: unit tests reuse the same revision across reject and resubmit actions
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: reject clears the active request and sets `approval_rejected`; resubmit creates a new request id and increments `approval_round`.

### T5: Add-sign is constrained to the active step

- Result: passed
- Covers: P2-AC4
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: service tests add a third cosigner while the active step is still `cosign`
- Evidence refs: `backend/tests/test_document_control_service_unit.py`
- Notes: add-sign rejects forbidden actors and duplicate approvers, and the injected approver must still act before the step completes.

### T6: Legacy direct transition endpoint is removed

- Result: passed
- Covers: P3-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: FastAPI `TestClient`
- Evidence refs: `backend/app/modules/document_control/router.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: `/quality-system/doc-control/revisions/{id}/transitions` is no longer routed, and the new `/approval/*` endpoints are exercised instead.

### T7: Required validation command passes

- Result: passed
- Covers: P4-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local Windows PowerShell / Python 3.12 test run
- Evidence refs: `20 passed in 13.36s`
- Notes: the WS01 backend service/API suite completed successfully after stabilizing the in-app notification assertions.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1; P2-AC1; P2-AC2; P2-AC3; P2-AC4; P3-AC1; P4-AC1
- Blocking prerequisites:
- Summary: WS01 backend workflow contract is implemented, legacy direct transitions are removed, and the targeted backend service/API suite passes.

## Open Issues

- No known WS01 blockers remain.
