# WS04 Department Ack And Execution Confirmation (Backend)

- Task ID: `ws04-implement-post-release-department-acknowled-20260414T224438`
- Created: `2026-04-14T22:44:38`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Input Contract:
  - `docs/tasks/document-control-flow-parallel-20260414T151500/ws04-department-ack-and-execution-confirmation.md`
  - `docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws04-department-ack-and-execution-confirmation.md`

## Goal

Implement the missing post-release department acknowledgment loop for Document Control:

- When a controlled revision becomes effective (the current code path that represents “release”), create per-department acknowledgment records.
- Notify each target department via in-app inbox notifications.
- Allow department users (or admins) to confirm receipt/execution with an audit trail.
- Provide explicit `pending` / `confirmed` / `overdue` semantics and a reminder action for overdue items.

## Scope

Owned paths (per WS04 prompt):

- `backend/app/modules/document_control/router.py`
- `backend/services/notification/`
- `backend/app/modules/inbox/router.py`
- `backend/tests/test_document_control_api_unit.py`

Shared integration paths (minimal touch; wiring only if needed):

- `backend/services/document_control/service.py`
- `backend/database/schema/document_control.py`
- `backend/database/schema/ensure.py`

## Non-Goals

- WS01 approval matrix / standardized review changes.
- WS02 training gate logic.
- WS03 release ledger / distribution ledger implementation.
- WS05 obsolete/retention/destruction lifecycle.
- Frontend implementation (UI/UX). API + in-app inbox payloads only.
- “Default to all departments” behavior.
- Reusing Change Control’s department confirmation semantics without adaptation.

## Preconditions

Must exist or must be configured; otherwise fail fast:

- `notification_channels` includes an enabled `in_app` channel (created by app dependency factory as `inapp-main` in normal runtime). Unit tests must create it explicitly.
- A stable target-department mapping for each controlled document exists in repo data (DB). If missing, attempting to “release” (effective transition) must error; no implicit “all departments”.
- At least one active user exists for each target department (recipient resolution). If a department has no active users, the release/reminder operation must fail with a clear error.

## Impacted Areas

- Document Control lifecycle: effective transition path (`DocumentControlService.transition_revision` -> `_make_revision_effective`).
- Notification catalog + rule seeding (add supported event types for department ack).
- Inbox listing visibility (ensure new event types are visible and have `title/body/link_path` in payload).
- Unit tests under `backend/tests/test_document_control_api_unit.py`.

## Phase Plan

### P1: Data Model And Schema

- Objective: Introduce a department acknowledgment data model and persisted target-department mapping.
- Owned paths:
  - `backend/database/schema/document_control.py`
  - `backend/database/schema/ensure.py` (only if required for registration)
- Dependencies:
  - Existing `controlled_documents` / `controlled_revisions` tables.
- Deliverables:
  - A new table for release department acknowledgments with audit fields.
  - An additive schema change to store a controlled document’s target department ids (no silent defaults).

### P2: Service + API (Ack Create/List/Confirm)

- Objective: Create acknowledgment rows after “release” (revision becomes effective), expose list + confirm APIs, enforce department ownership.
- Owned paths:
  - `backend/services/document_control/service.py`
  - `backend/app/modules/document_control/router.py`
- Dependencies:
  - P1 schema.
- Deliverables:
  - Ack creation on effective transition with `pending` status and due time.
  - Listing endpoints for a revision’s department acks.
  - Confirmation endpoint enforcing `ctx.user.department_id` match (or admin override) and writing `confirmed_by/confirmed_at/notes`.

### P3: Notification + Reminder Semantics

- Objective: Departments receive in-app inbox notifications on creation and on overdue reminders; overdue state is explicit and auditable.
- Owned paths:
  - `backend/services/notification/event_catalog.py`
  - `backend/services/notification/code_defaults.py` (only if we need explicit defaults)
  - `backend/services/document_control/service.py`
- Dependencies:
  - P2 ack creation/list/confirm.
- Deliverables:
  - Supported notification event types for department-ack created + overdue reminder.
  - Reminder API that marks overdue items and dispatches reminder notifications with dedupe keys.

### P4: Tests

- Objective: Provide unit tests for ack creation, confirmation, and reminder behavior.
- Owned paths:
  - `backend/tests/test_document_control_api_unit.py`
- Dependencies:
  - P1–P3.
- Deliverables:
  - Passing unit tests per WS04 validation target.

## Phase Acceptance Criteria

### P1

- P1-AC1: Schema includes a persisted department-ack model with `pending/confirmed/overdue` fields and audit fields (department, release revision, confirmer, timestamps, notes).
- P1-AC2: Target departments are stored in repo data (DB) and release fails fast if they are missing; no “all departments” default exists.
- Evidence expectation: `backend/database/schema/document_control.py` updated; tests demonstrate fail-fast behavior.

### P2

- P2-AC1: Transition to `effective` creates department ack rows for the configured target departments (one per department) with `pending` status and due time.
- P2-AC2: Confirmation endpoint updates the correct ack row, is idempotent for repeat confirms, and rejects users whose `department_id` does not match (unless admin).
- Evidence expectation: `backend/tests/test_document_control_api_unit.py` covers create+confirm.

### P3

- P3-AC1: Notification event types are introduced and used; upon ack creation, each target department receives an in-app inbox item with `title/body/link_path` in payload.
- P3-AC2: Reminder action marks overdue acks explicitly and creates reminder inbox items; reminder action is auditable (via existing audit log store/manager if present).
- Evidence expectation: tests assert inbox items created and overdue transition occurs.

### P4

- P4-AC1: `python -m pytest backend/tests/test_document_control_api_unit.py -q` passes.
- Evidence expectation: `test-report.md` includes command output and pass verdict.

## Done Definition

- All phases `P1`–`P4` are completed and recorded in `execution-log.md`.
- Every acceptance id `P1-AC1`..`P4-AC1` has evidence references in `execution-log.md` and/or `test-report.md`.
- Unit tests specified in WS04 prompt pass.

## Blocking Conditions

- Cannot resolve target department ids from persisted repo data (DB) for a document being released.
- Any target department has no resolvable active user recipients.
- Notification system is missing an enabled `in_app` channel.
- Attempted implementation introduces fallback behavior (e.g., defaulting to “all departments”) or silently downgrades failure to success.
