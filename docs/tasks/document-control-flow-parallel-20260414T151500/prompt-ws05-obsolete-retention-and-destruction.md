# Executor Prompt: WS05 Obsolete Retention And Destruction

You are executing `WS05` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws03-controlled-release-and-distribution.md`
3. `ws05-obsolete-retention-and-destruction.md`
4. `docs/compliance/release_and_retirement_sop.md`
5. `docs/compliance/retirement_plan.md`

## Mission

Define and implement the controlled obsolete, retention, and destruction path for document control without faking compliance coverage that the repo does not actually own.

## Current Repo Facts

- Current document-control obsolete behavior is not a full obsolete-approval lifecycle.
- Standard knowledge preview and download primarily gate on `archived`, not document-control obsolete state.
- Existing compliance docs still describe part of retirement and destruction as outside-repo residual work.

## Owned Paths

- `backend/services/compliance/retired_records.py`
- `backend/app/modules/knowledge/routes/retired.py`
- `backend/app/modules/knowledge/routes/files.py`
- `backend/services/document_control/service.py`
- `docs/compliance/release_and_retirement_sop.md`
- `docs/compliance/retirement_plan.md`
- `backend/tests/test_document_control_api_unit.py`

## Shared Integration Paths

- `backend/database/schema/document_control.py`
- `backend/database/schema/ensure.py`
- `backend/app/modules/document_control/router.py`

## Must Deliver

- explicit obsolete initiation and approval path
- explicit access policy during retention
- explicit retention-until fields
- either destruction implementation with records or a documented fail-fast boundary if destruction must remain outside the system
- aligned code and compliance documentation

## Non-Goals

- approval matrix
- training gate
- release ledger
- department confirmation
- frontend implementation

## Fail-Fast Rules

- If system-owned destruction is not approved by requirements, do not implement silent auto-delete.
- Do not claim in code or docs that destruction is complete if it still requires offline action.
- Do not keep the old direct `effective -> obsolete` transition as the full obsolete contract.

## Validation Target

```powershell
python -m pytest `
  backend/tests/test_document_control_api_unit.py `
  backend/tests/test_retired_document_access_unit.py -q
```

## Required Final Handoff

- changed paths
- obsolete / retention / destruction contract
- doc updates made
- validations run
- unresolved blockers
