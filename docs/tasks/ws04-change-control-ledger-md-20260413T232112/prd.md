# PRD: WS04 Change Control Ledger Implementation

- Task ID: `ws04-change-control-ledger-md-20260413T232112`
- Created: `2026-04-13T23:21:12`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成WS04-change-control-ledger.md下的工作`

## Goal

Implement the WS04 change-control ledger workflow in real code so users can create a change request, manage plan items, send due reminders, perform cross-department confirmation, and close with ledger writeback evidence.

## Scope

- Backend API and service for WS04 workflow under new module namespace:
  - `backend/app/modules/change_control/*`
  - `backend/services/change_control/*`
  - `backend/database/schema/change_control.py`
- Dependency wiring and app router registration:
  - `backend/app/dependency_factory.py`
  - `backend/database/schema/ensure.py`
  - `backend/app/main.py`
- Frontend feature + page for WS04 route surface:
  - `fronted/src/features/changeControl/*`
  - `fronted/src/pages/ChangeControl.js`
  - `fronted/src/pages/QualitySystem.js`
- Unit tests for backend and frontend WS04 behavior.

## Non-Goals

- Do not modify `fronted/src/routes/routeRegistry.js`.
- Do not modify `backend/app/core/permission_models.py`.
- Do not modify `backend/app/modules/audit/*`.
- Do not modify `backend/services/compliance/*`.
- Do not redesign global notification schema; reuse existing inbox/notification payload structures.
- Do not remove or rewrite existing `emergency_changes` behavior.

## Preconditions

- Python runtime and backend unit-test dependencies are available.
- Frontend test runtime (`npm`/`node`, jest/react scripts) is available.
- `backend/database/schema/ensure.py` can be executed during tests for schema bootstrap.
- Existing auth/dependency wiring remains functional.

If any precondition fails, execution must stop and the missing item must be recorded in `task-state.json.blocking_prereqs`.

## Impacted Areas

- Existing emergency-change service patterns used as baseline:
  - `backend/services/emergency_change.py`
  - `backend/app/modules/emergency_changes/router.py`
- Existing quality-system shell route and module selection:
  - `fronted/src/features/qualitySystem/moduleCatalog.js`
  - `fronted/src/features/qualitySystem/useQualitySystemPage.js`
  - `fronted/src/pages/QualitySystem.js`
- Existing HTTP and feature API patterns:
  - `fronted/src/shared/http/httpClient.js`
  - `fronted/src/features/maintenance/api.js`
- Existing tests style:
  - `backend/tests/test_emergency_change_api_unit.py`
  - `fronted/src/pages/*test.js`

## Phase Plan

### P1: Backend WS04 Ledger and Workflow API

- Objective: Deliver WS04 backend data model and workflow transitions including change requests, plan items, reminders, cross-department confirmation, and closure writeback fields.
- Owned paths:
  - `backend/database/schema/change_control.py`
  - `backend/database/schema/ensure.py`
  - `backend/services/change_control/*`
  - `backend/app/modules/change_control/*`
  - `backend/app/dependency_factory.py`
  - `backend/app/main.py`
  - `backend/tests/test_change_control_api_unit.py`
- Dependencies:
  - existing SQLite schema bootstrap mechanism
  - existing `UserInboxService` from app dependencies
- Deliverables:
  - CRUD + transition APIs for change requests
  - plan-item management API
  - due reminder dispatch endpoint using existing inbox payload structure
  - cross-department confirmation endpoint
  - close endpoint with ledger writeback fields and controlled-revision references

### P2: Frontend WS04 Page and API Client

- Objective: Expose WS04 workflow from `/quality-system/change-control` without changing route registry wiring.
- Owned paths:
  - `fronted/src/features/changeControl/*`
  - `fronted/src/pages/ChangeControl.js`
  - `fronted/src/pages/QualitySystem.js`
- Dependencies:
  - existing quality-system module path mapping in route catalog
  - backend APIs from P1
- Deliverables:
  - change-control API client
  - page for request creation/listing and key transitions
  - quality-system conditional rendering that loads WS04 page on change-control subroute

### P3: Verification and Task Artifacts Completion

- Objective: Validate WS04 implementation with unit tests and update task evidence artifacts.
- Owned paths:
  - `backend/tests/test_change_control_api_unit.py`
  - `fronted/src/features/changeControl/api.test.js`
  - `fronted/src/pages/ChangeControl.test.js`
  - `docs/tasks/ws04-change-control-ledger-md-20260413T232112/execution-log.md`
  - `docs/tasks/ws04-change-control-ledger-md-20260413T232112/test-report.md`
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - passing backend and frontend WS04 tests
  - execution/test evidence recorded for each acceptance id

## Phase Acceptance Criteria

### P1

- P1-AC1: Backend exposes `change_control` APIs for create/list/get workflow requests with strict required-field validation.
- P1-AC2: Backend supports plan-item create/update/list and enforces parent request state rules.
- P1-AC3: Backend supports due reminder dispatch using existing inbox notification structure (no custom notification schema).
- P1-AC4: Backend supports cross-department confirmation and transition to closable state.
- P1-AC5: Backend close operation records ledger writeback fields, controlled revision references, and closure metadata.
- Evidence expectation: API unit tests cover happy-path and guard-path transitions, with execution log entries listing commands and changed paths.

### P2

- P2-AC1: `/quality-system/change-control` renders WS04 feature page instead of placeholder shell content.
- P2-AC2: Frontend change-control API client maps backend response contracts and propagates backend errors.
- P2-AC3: WS04 page supports at least create request, add plan item, dispatch reminders, confirm, and close actions.
- Evidence expectation: frontend unit tests validate rendering and API interaction behavior.

### P3

- P3-AC1: Backend WS04 tests pass in local repo test run.
- P3-AC2: Frontend WS04 tests pass in local repo test run.
- P3-AC3: `execution-log.md` and `test-report.md` contain acceptance-id traceable evidence for P1/P2/P3 criteria.
- Evidence expectation: concrete command outputs summarized in test report and referenced from state evidence entries.

## Done Definition

Task is complete only when:

- P1/P2/P3 statuses are all `completed`.
- All acceptance ids (P1-AC1..P1-AC5, P2-AC1..P2-AC3, P3-AC1..P3-AC3) are `completed`.
- Backend and frontend WS04 test commands pass.
- `test_status` is `passed` and completion gate script reports success.

## Blocking Conditions

- Missing Python or frontend test runtime required to execute validation commands.
- Schema bootstrap failure for WS04 tables.
- Inability to wire dependencies/router without touching forbidden files listed in WS04 non-goals.
- Any requirement that would force fallback/mocked behavior instead of real workflow implementation.
