# Users Manager Refactor Test Plan

- Task ID: `tranche-backend-services-users-manager-py-create-20260408T075138`
- Created: `2026-04-08T07:51:38`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：本 tranche 聚焦 backend/services/users/manager.py，抽离 create/update 共用的用户组织、角色、权限组与禁用策略解析逻辑，保持用户管理对外行为和现有单测契约稳定`

## Test Scope

Validate that the bounded backend refactor preserves:

- duplicate username error mapping during create
- manager/sub-admin and managed-root validation during create/update
- builtin-admin disable guard behavior
- disable schedule validation behavior

Out of scope:

- router-level API tests
- live database integration beyond the existing fake-port unit coverage
- unrelated auth or password flows

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python with `py_compile` and `pytest`
- Test runtime: fake ports and unit fixtures already embedded in the focused test modules

## Accounts and Fixtures

- tests rely on fake `UsersPort` implementations inside the focused unit files
- no live database or external service is required
- if Python, `py_compile`, or `pytest` is unavailable, fail fast and record the missing
  prerequisite

## Commands

- `python -m py_compile backend/services/users/manager.py backend/services/users/manager_support.py`
  - Expected success signal: edited users-manager modules compile without syntax errors
- `python -m pytest backend/tests/test_users_manager_create_duplicate_unit.py backend/tests/test_users_manager_manager_user_unit.py backend/tests/test_users_manager_admin_guard.py backend/tests/test_users_manager_disable_schedule_unit.py -q`
  - Expected success signal: focused users-manager suites pass

## Test Cases

### T1: Users manager business-rule regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit
- Command: `python -m pytest backend/tests/test_users_manager_create_duplicate_unit.py backend/tests/test_users_manager_manager_user_unit.py backend/tests/test_users_manager_admin_guard.py backend/tests/test_users_manager_disable_schedule_unit.py -q`
- Expected: helper extraction preserves the existing create/update business-rule behavior and
  stable business errors

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend users manager | shared create/update helper extraction preserves user mutation business rules | unit | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, py_compile, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused backend commands against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the compile command succeeds
  - T1 passes
  - business-rule errors and role behavior remain unchanged
- Fail when:
  - either command fails
  - create/update business rules or stable errors regress

## Regression Scope

- `backend/services/users/manager.py`
- new helper module(s) under `backend/services/users/`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each command passed.
