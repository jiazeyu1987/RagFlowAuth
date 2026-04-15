# WS03 PRD: Controlled Release And Distribution Ledger

- Task ID: `docs-tasks-document-control-flow-parallel-202604-20260414T224329`
- Created: `2026-04-14T22:43:29`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws03-controlled-release-and-distribution.md 下的工作`

## Goal

Introduce an explicit controlled release (publish) action and a release ledger for document-control revisions, replacing the legacy behavior where a revision becoming `effective` implicitly obsoletes the previous effective revision without any release record.

Key outcomes:

- Publish/release is a distinct action that requires:
  - WS01 approval completion (`approved_pending_effective`)
  - WS02 training gate satisfaction (fail fast; no bypass)
- Release ledger persists:
  - mode (`automatic` vs `manual_by_doc_control`)
  - actor + timestamp
  - target revision + replaced revision relationship
- Replaced effective revisions are **superseded** (not lifecycle-`obsolete`) and carry explicit supersede metadata.

## Scope

- Backend schema changes for document control:
  - add a release ledger table
  - add supersede metadata fields on revisions
- Backend service behavior:
  - explicit publish/release action
  - validation gates for approval completion + training gate
  - replace “previous effective becomes obsolete” with “previous effective becomes superseded”
- Backend API surface:
  - expose explicit publish endpoint
  - expose the required approval endpoints so API tests can reach the pre-release state
- Tests:
  - update service unit tests + API unit tests to validate the above

## Non-Goals

- Change the approval matrix semantics or step ordering (WS01 owns the contract)
- Implement training assignment/ack logic itself (WS02 owns it)
- Department acknowledgment / execution confirmation (WS04)
- Obsolete / retention / destruction lifecycle policy (WS05)
- Frontend wiring (WS06)
- Any fallback path that keeps legacy direct transitions “quietly working”

## Preconditions

These are hard prerequisites; missing items must fail fast (no fallback, no silent downgrade).

- `ensure_schema()` is used in runtime/tests so additive schema changes apply.
- WS01 approval prerequisites are available:
  - `deps.document_control_approval_matrix` is configured (no default/fallback introduced here).
  - `deps.user_store.get_by_user_id(user_id)` is available and returns active users for approver ids referenced by the workflow.
- WS02 training gate prerequisites are available:
  - `deps.training_compliance_service` exists.
  - At least one training requirement exists for:
    - `controlled_action = "document_review"`
    - the release actor’s `role_code`
  - Release actor has:
    - a passing training record
    - an active certification for the requirement

If any prerequisite is missing, publish must fail fast and the blocker must be recorded in `task-state.json.blocking_prereqs`.

## Impacted Areas

- Schema: `backend/database/schema/document_control.py`
- Service: `backend/services/document_control/service.py`
- Models: `backend/services/document_control/models.py`
- API router: `backend/app/modules/document_control/router.py`
- Tests:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`
- Shared integration awareness (do not expand scope):
  - `backend/services/compliance/review_package.py` (future consumer of release ledger)

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: Add release ledger schema + supersede fields

- Objective: Persist explicit release/distribution records and model supersede metadata on replaced revisions.
- Owned paths:
  - `backend/database/schema/document_control.py`
  - `backend/services/document_control/models.py`
- Dependencies: none
- Deliverables:
  - new table `controlled_revision_release_ledger`
  - additive columns on `controlled_revisions` for supersede metadata
  - loaders/models expose those fields

### P2: Implement explicit publish action + supersede semantics

- Objective: Implement a publish action that makes an approved revision effective, writes ledger rows, and supersedes the previous effective revision without using lifecycle `obsolete`.
- Owned paths:
  - `backend/services/document_control/service.py`
- Dependencies: P1
- Deliverables:
  - `publish_revision()` validates:
    - approval completed (`approved_pending_effective`)
    - training gate satisfied (fail fast if not configured / not met)
  - release ledger rows written for:
    - published revision
    - superseded previous effective revision (when applicable)
  - previous effective revision becomes `superseded` with timestamp + source revision id

### P3: Expose publish API + required approval endpoints

- Objective: Provide explicit API endpoints to drive the flow without legacy `/transitions`.
- Owned paths:
  - `backend/app/modules/document_control/router.py`
- Dependencies: P2
- Deliverables:
  - `POST /quality-system/doc-control/revisions/{id}/approval/submit`
  - `POST /quality-system/doc-control/revisions/{id}/approval/approve`
  - `POST /quality-system/doc-control/revisions/{id}/approval/reject`
  - `POST /quality-system/doc-control/revisions/{id}/approval/add-sign`
  - `POST /quality-system/doc-control/revisions/{id}/publish` (explicit release action, includes `release_mode`)
  - legacy `/transitions` remains removed/disabled (no compatibility fallback)

### P4: Update unit + API tests

- Objective: Prove the controlled release contract and ledger behavior via the required pytest targets.
- Owned paths:
  - `backend/tests/test_document_control_service_unit.py`
  - `backend/tests/test_document_control_api_unit.py`
- Dependencies: P3
- Deliverables:
  - tests cover publish gating + ledger writes + supersede semantics
  - required pytest command passes

## Phase Acceptance Criteria

### P1

- P1-AC1: `ensure_document_control_tables()` creates the release ledger table and indexes, and adds revision supersede columns additively.
- P1-AC2: `ControlledRevision.as_dict()` includes supersede metadata fields populated from DB rows.
- Evidence expectation: schema + model changes exist and are referenced by tests/service load paths.

### P2

- P2-AC1: Publish rejects when the revision is not `approved_pending_effective` (approval completion is not treated as release).
- P2-AC2: Publish enforces the training gate: missing `training_compliance_service` or missing requirements/records/certification blocks publish (no bypass).
- P2-AC3: Publish writes release ledger rows including mode/actor/time/target + replaced revision id, and makes the revision `effective` with `effective_at_ms`.
- P2-AC4: When a new revision is published over an existing effective one, the previous effective becomes `superseded` (not `obsolete`) with `superseded_at_ms` and `superseded_by_revision_id`.
- Evidence expectation: service unit test asserts gating + ledger rows + supersede semantics.

### P3

- P3-AC1: Router exposes explicit publish endpoint and required approval endpoints; legacy `/transitions` is not available as a working path.
- Evidence expectation: API unit test uses explicit endpoints end-to-end.

### P4

- P4-AC1: The command below passes:

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

- Evidence expectation: `test-report.md` contains a pass verdict and command output summary.

## Done Definition

- All phases P1–P4 are completed with evidence recorded in `execution-log.md` and `test-report.md`.
- Publish/release is explicit via a publish endpoint and release ledger rows exist for publishes/supersedes.
- Previous effective revisions are superseded (not lifecycle-obsoleted) when replaced by a newer published revision.
- No fallback/compat path exists that allows legacy direct transitions to keep working silently.

## Blocking Conditions

- Missing `deps.training_compliance_service` or missing training requirements (must block publish).
- Missing `deps.document_control_approval_matrix` or `deps.user_store` (must block approval submission, which blocks publish prerequisites).
- Database schema cannot be updated additively via `ensure_schema()` in the target environment.
