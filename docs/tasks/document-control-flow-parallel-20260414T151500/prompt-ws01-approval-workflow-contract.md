# Executor Prompt: WS01 Approval Workflow Contract

You are executing `WS01` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws01-approval-workflow-contract.md`

## Mission

Replace the current direct document-control status progression with a workflow-driven approval contract that supports:

- cosign
- approve
- standardization review
- reject and restart semantics
- add-sign behavior

You must freeze this contract for all later packages. Do not leave any ambiguity for downstream work.

## Current Repo Facts

- Current document control status flow is hard-coded in `backend/services/document_control/service.py`.
- Current router exposes direct transitions in `backend/app/modules/document_control/router.py`.
- Existing reusable approval engine lives under `backend/services/operation_approval/`.

## Owned Paths

- `backend/services/operation_approval/`
- `backend/app/modules/operation_approvals/router.py`
- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/document_control.py`
- `backend/tests/test_document_control_service_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/ensure.py`
- `backend/app/main.py`

Use shared integration paths only for registration and wiring.

## Must Deliver

- explicit workflow contract for document-control revisions
- workflow-backed submit / approve / reject / resubmit behavior
- explicit standardization-review step
- explicit audit trail for submit, activate, approve, reject, resubmit, add-sign
- tests proving order and rejection semantics

## Non-Goals

- training workflow
- release / publish ledger
- department acknowledgment
- obsolete / retention / destruction
- frontend workspace redesign

## Fail-Fast Rules

- If the approval engine cannot represent the required step types or add-sign behavior, stop and report the exact gap.
- If matrix resolution inputs are missing, reject submission explicitly.
- Do not keep the old direct transition buttons or endpoints as hidden compatibility behavior.

## Validation Target

Run narrow backend tests first:

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

## Required Final Handoff

- changed paths
- exact workflow states and events introduced
- validations run
- unresolved blockers
