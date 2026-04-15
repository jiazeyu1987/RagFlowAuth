# worker-01 Task

## Goal

Execute `WS01` from `docs/tasks/document-control-flow-parallel-20260414T151500/ws01-approval-workflow-contract.md`.

Replace the current direct document-control status progression with a workflow-driven approval contract that supports:

- cosign
- approve
- standardization review
- reject and restart semantics
- add-sign behavior

You must freeze this contract for all later workstreams. Do not leave ambiguity for downstream workers.

## Owned Paths

- `backend/services/operation_approval/`
- `backend/app/modules/operation_approvals/router.py`
- `backend/services/document_control/service.py`
- `backend/app/modules/document_control/router.py`
- `backend/database/schema/document_control.py`
- `backend/tests/test_document_control_service_unit.py`
- `backend/tests/test_document_control_api_unit.py`

## Do Not Modify

- Any path not listed in Owned Paths is out of scope unless the supervisor updates this file.
- In shared integration paths, restrict changes to the smallest required registration or wiring updates.
- Do not revert unrelated user changes in owned files; adapt to them.

## Dependencies

- Read `docs/tasks/document-control-flow-parallel-20260414T151500/README.md`.
- Read `docs/tasks/document-control-flow-parallel-20260414T151500/ws01-approval-workflow-contract.md`.
- Existing approval engine is under `backend/services/operation_approval/`.
- Later workstreams depend on the states, events, and rejection semantics you freeze here.

## Acceptance Criteria

- Replace direct document-control transition semantics with a workflow-backed contract.
- Support explicit `cosign`, `approve`, and `standardize_review` step types.
- Make rejection terminate the current approval instance and preserve restart semantics.
- Add explicit audit trail for submit, activate, approve, reject, resubmit, and add-sign.
- Remove hidden compatibility behavior that still lets callers rely on raw direct status progression.
- Validation must pass.
- Supervisor review must pass.
- Update `progress.md` at required milestones and refresh `state.json` each time.

## Validation

Run this exact narrow command before marking ready for validation:

```powershell
python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q
```

Record the exact command and result in `progress.md`.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

### Corrective Guidance Round 1

- Your owned code paths show substantive edits, but you have not appended any milestone progress since 2026-04-14T13:56:53Z.
- Immediately append a progress entry that summarizes:
  - the concrete changes already made
  - the files touched so far
  - whether you are blocked or still implementing
- Immediately refresh `state.json.updated_at` and `current_step`.
- If you are blocked, mark `status` as `blocked` and state the exact blocker in `progress.md`.
- If you are still implementing, continue after syncing `.super` files and stop at `ready_for_validation` only after the pytest command passes.

## Supervisor Notes

- `.super` files are authoritative for this run.
- Append progress when you start work, reach a key milestone, hit a blocker, and become ready for validation.
- Update `.super/runs/document-control-flow-20260414T133900Z/workers/worker-01/state.json` alongside every progress entry.
- Stop at `ready_for_validation`; do not declare yourself passed.
