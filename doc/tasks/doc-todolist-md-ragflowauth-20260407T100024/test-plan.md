# Approval Domain Refactor Test Plan

- Task ID: `doc-todolist-md-ragflowauth-20260407T100024`
- Created: `2026-04-07T10:00:24`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `按照 doc/todolist.md 下的描述逐个进行代码重构修复，当前阶段聚焦审批域。`

## Test Scope

- Validate backend approval-flow refactors in `backend/services/operation_approval/`.
- Validate transaction boundaries, collaborator delegation, explicit approval models, router registration, and targeted approval regressions.
- Keep frontend, dependency assembly, and later todolist items outside this validation pass.

## Environment

- Python 3.12 on Windows with repository dependencies already installed.
- Local SQLite test databases created by `backend.database.schema.ensure.ensure_schema`.
- No live external services required; notification, inbox, signature, and knowledge dependencies are exercised through existing unit-test fixtures.
- If `python -m unittest` cannot run, or the backend test schema cannot be initialized, fail fast and record the blocking prerequisite in `task-state.json`.

## Accounts and Fixtures

- Admin applicant fixture from `backend.tests.test_operation_approval_service_unit`.
- Reviewer fixtures `approver_1`, `approver_2`, `approver_3`.
- Managed-path upload fixtures under `data/test_operation_approval/...`.
- Seed knowledge-base datasets and documents created by the test helpers in `backend/tests/test_operation_approval_service_unit.py`.

## Commands

- `python -m unittest backend.tests.test_operation_approval_service_unit`
  Expected success signal: `Ran 34 tests` and `OK`.
- `python -m unittest backend.tests.test_operation_approval_router_unit`
  Expected success signal: `Ran 1 test` and `OK`.

## Test Cases

### T1: Transaction Rollback Boundaries

- Covers: P1-AC1, P1-AC2
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_service_unit`
- Expected: approve, reject, withdraw, and execution-start rollback tests leave request, step, approver, and event state unchanged when event writes fail.

### T2: Approval Execution Regression

- Covers: P1-AC3, P2-AC3, P3-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_service_unit`
- Expected: single-step, multi-step, any-rule, auto-skip, execute-success, and execute-failure approval flows preserve prior behavior.

### T3: Collaborator Delegation

- Covers: P2-AC1, P2-AC2, P3-AC1, P3-AC2
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_service_unit`
- Expected: migration, audit, notification, execution, and decision collaborators are invoked through the orchestrating service and the service no longer owns the detailed state-transition logic inline.

### T4: Router Compatibility

- Covers: P2-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_router_unit`
- Expected: approval router registration and public API behavior remain unchanged after service refactoring.

### T5: Notification And Audit Persistence

- Covers: P2-AC1, P2-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_service_unit`
- Expected: submission, pending-approval, final-result notifications and audit records are still persisted through the extracted collaborators.

### T6: Explicit Approval Models

- Covers: P4-AC1, P4-AC2, P4-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_operation_approval_service_unit`
- Expected: request, step, workflow, and event model tests confirm the main approval path uses explicit models instead of ad hoc dict-key access while preserving prior behavior.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | approval transactions | rollback on event-write failure | unit | P1-AC1, P1-AC2 | `execution-log.md#phase-p1`, `test-report.md#test-cycle-2026-04-07` |
| T2 | approval workflow | approve, reject, withdraw, and execute regressions | unit | P1-AC3, P2-AC3, P3-AC3 | `execution-log.md#phase-p3`, `test-report.md#test-cycle-2026-04-07` |
| T3 | service decomposition | collaborator delegation | unit | P2-AC1, P2-AC2, P3-AC1, P3-AC2 | `execution-log.md#phase-p2`, `execution-log.md#phase-p3`, `test-report.md#test-cycle-2026-04-07` |
| T4 | router compatibility | router unit regression | unit | P2-AC3 | `test-report.md#test-cycle-2026-04-07` |
| T5 | side effects | notifications and audit persistence | unit | P2-AC1, P2-AC3 | `test-report.md#test-cycle-2026-04-07` |
| T6 | explicit models | typed approval-model validation | unit | P4-AC1, P4-AC2, P4-AC3 | `execution-log.md#phase-p4`, `test-report.md#test-cycle-2026-04-07` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, unittest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run the current working tree against the real repository tests and local SQLite-backed unit fixtures. Do not replace failing prerequisites with fallback paths, mocks, or assumed success.
- Escalation rule: If the evaluator cannot run a required command or validate a case from repository context, stop immediately and record the exact blocker in `test-report.md`.

## Pass / Fail Criteria

- Pass when both targeted backend approval commands complete successfully, every planned case has a passing result, and the covered acceptance ids have matching evidence in `execution-log.md` or `test-report.md`.
- Fail when any approval state regression, transaction rollback regression, collaborator wiring failure, router regression, or explicit-model regression is observed.

## Regression Scope

- Approval request creation, approval, rejection, withdrawal, execution start, execution finish, and execution failure paths.
- Notification and audit side effects driven by approval events.
- Legacy document-review migration delegation.
- Router-level approval endpoints.

## Reporting Notes

- Write concrete command output summaries and acceptance coverage to `test-report.md`.
- The tester must remain independent from execution evidence on the first pass and only inspect withheld artifacts after recording an initial verdict.
