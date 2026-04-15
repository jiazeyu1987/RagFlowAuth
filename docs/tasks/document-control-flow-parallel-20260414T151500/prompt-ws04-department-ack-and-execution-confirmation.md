# Executor Prompt: WS04 Department Ack And Execution Confirmation

You are executing `WS04` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws03-controlled-release-and-distribution.md`
3. `ws04-department-ack-and-execution-confirmation.md`

## Mission

Add the missing post-release department acknowledgment loop required by the target process:

- release creates department confirmation items
- departments receive notification
- departments confirm execution or receipt
- overdue items can be reminded and audited

## Current Repo Facts

- Document control currently has no department-confirmation model.
- Change control has a cross-department confirmation flow, but its semantics are different and must not be copied blindly.

## Owned Paths

- `backend/app/modules/document_control/router.py`
- `backend/services/notification/`
- `backend/app/modules/inbox/router.py`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/services/document_control/service.py`
- `backend/database/schema/document_control.py`
- `backend/database/schema/ensure.py`

## Must Deliver

- department acknowledgment data model
- creation of acknowledgment items after release
- notification or inbox integration
- explicit pending, confirmed, overdue semantics
- tests for creation, confirmation, and reminder behavior

## Non-Goals

- approval matrix
- training gate logic
- release ledger logic itself
- obsolete / destruction lifecycle
- frontend implementation

## Fail-Fast Rules

- If department ownership cannot be resolved from repo data, stop and report the missing prerequisite.
- Do not reuse change-control confirmation semantics unless they are explicitly adapted for document control.
- Do not default to “all departments” when the target list is unknown.

## Validation Target

```powershell
python -m pytest backend/tests/test_document_control_api_unit.py -q
```

## Required Final Handoff

- changed paths
- department acknowledgment state contract
- notification event types introduced
- validations run
- unresolved blockers
