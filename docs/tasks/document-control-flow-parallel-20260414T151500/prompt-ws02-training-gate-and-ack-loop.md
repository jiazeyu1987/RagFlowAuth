# Executor Prompt: WS02 Training Gate And Ack Loop

You are executing `WS02` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws01-approval-workflow-contract.md`
3. `ws02-training-gate-and-ack-loop.md`

## Mission

Turn training from a post-effective side flow into an explicit document-control gate that later release logic can consume.

The target workflow requires:

- conditional training requirement
- assignee selection
- reading and acknowledgment
- question thread loop
- auditable training record

## Current Repo Facts

- Current training assignments are tied to effective revisions in `backend/services/training_compliance.py`.
- Current assignment generation defaults to all active users when assignees are omitted.

## Owned Paths

- `backend/services/training_compliance.py`
- `backend/app/modules/training_compliance/router.py`
- `backend/database/schema/training_ack.py`
- `backend/database/schema/training_compliance.py`
- `backend/tests/test_training_compliance_api_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/ensure.py`

## Must Deliver

- explicit training gate states for document-control revisions
- explicit blocking behavior when required training is incomplete
- no implicit default-to-all assignment unless that is confirmed by explicit requirements
- preserved question-thread and read-time controls
- tests proving training gate behavior

## Non-Goals

- approval matrix and add-sign behavior
- release ledger
- department acknowledgment
- obsolete / retention / destruction
- frontend implementation

## Fail-Fast Rules

- If department-based assignee resolution lacks a stable data source, stop and report it.
- If the business rule “training blocks release” is contradicted by local requirements, stop and report it instead of silently preserving current behavior.
- Do not keep the old “effective first, training later” flow as a hidden fallback.

## Validation Target

```powershell
python -m pytest `
  backend/tests/test_training_compliance_api_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

## Required Final Handoff

- changed paths
- training gate state contract
- validations run
- unresolved blockers
