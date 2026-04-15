# Execution Log

- Task ID: `docs-tasks-document-control-flow-parallel-202604-20260414T224329`
- Created: `2026-04-14T22:43:29`

## Phase Entries

Append one reviewed section per executor pass using real phase ids and real evidence refs.

### P1: Add release ledger schema + supersede fields

- Status: completed
- Changes:
  - Added `controlled_revision_release_ledger` table and indexes.
  - Added `superseded_at_ms` + `superseded_by_revision_id` to `controlled_revisions`.
  - Extended `ControlledRevision` model + service loaders to expose supersede metadata.
- Evidence:
  - `backend/database/schema/document_control.py` updated.
  - `backend/services/document_control/models.py` updated.
  - `backend/services/document_control/service.py` loads the new columns.

### P2: Implement explicit publish action + supersede semantics

- Status: completed
- Changes:
  - Implemented `DocumentControlService.publish_revision()` with:
    - approval completion gate (`approved_pending_effective`)
    - training gate via `training_compliance_service.assert_user_authorized_for_action(..., controlled_action=\"document_review\")`
    - required `release_mode` (`automatic` / `manual_by_doc_control`)
  - Updated `_make_revision_effective()` to:
    - supersede the previous effective revision (status `superseded`) instead of marking it lifecycle-`obsolete`
    - write `controlled_revision_release_ledger` rows for `published` + `superseded`
    - emit audit events `controlled_revision_published` + `controlled_revision_superseded`
  - Disabled legacy `make_revision_effective()` entrypoint (410) to force explicit publish.
- Evidence:
  - `backend/services/document_control/service.py` updated (publish, ledger writes, supersede semantics).

### P3: Expose publish API + required approval endpoints

- Status: completed
- Changes:
  - Added explicit publish endpoint: `POST /quality-system/doc-control/revisions/{id}/publish` requiring `release_mode`.
  - Wired publish endpoint to `DocumentControlService.publish_revision()` and capability action `document_control:publish`.
- Evidence:
  - `backend/app/modules/document_control/router.py` updated (new request model + endpoint wiring).

### P4: Update unit + API tests

- Status: completed
- Changes:
  - Updated service tests to cover:
    - publish invalid-status gate
    - training gate fail-fast
    - release ledger rows
    - supersede semantics
  - Updated API tests to use the explicit `/publish` endpoint and keep compatibility with the current publish-time distribution/department-ack flow.
- Evidence:
  - `backend/tests/test_document_control_service_unit.py` updated.
  - `backend/tests/test_document_control_api_unit.py` updated.
  - `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q` -> `20 passed in 14.09s`.

## Outstanding Blockers

- None yet.
