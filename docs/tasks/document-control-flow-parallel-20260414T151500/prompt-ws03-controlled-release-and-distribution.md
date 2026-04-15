# Executor Prompt: WS03 Controlled Release And Distribution

You are executing `WS03` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws01-approval-workflow-contract.md`
3. `ws02-training-gate-and-ack-loop.md`
4. `ws03-controlled-release-and-distribution.md`

## Mission

Introduce an explicit controlled release action and release ledger for document control. Replace the current behavior where making a revision effective implicitly obsoletes the previous effective revision without a release record.

## Current Repo Facts

- Current effective transition is implemented directly in `backend/services/document_control/service.py`.
- Previous effective revisions are auto-marked obsolete as part of that transition.
- There is no release ledger, manual mode, or distribution record.

## Owned Paths

- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/document_control.py`
- `backend/tests/test_document_control_service_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/ensure.py`
- `backend/services/compliance/review_package.py`

## Must Deliver

- explicit publish or release action
- explicit validation that approval is complete and training gate is satisfied
- release ledger
- automatic vs manual-by-document-control mode
- explicit supersede or recall records for replaced revisions

## Non-Goals

- workflow matrix changes
- training ack logic itself
- department confirmation
- obsolete / destruction lifecycle
- frontend implementation

## Fail-Fast Rules

- Do not treat approval completion as automatic release.
- Do not continue using raw `effective` transition as the only release record.
- If training gate data is unavailable, stop release instead of bypassing it.

## Validation Target

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

## Required Final Handoff

- changed paths
- release action and ledger schema
- validations run
- unresolved blockers
