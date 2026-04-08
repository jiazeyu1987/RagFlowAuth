# User Store Refactor Test Plan

- Task ID: `backend-services-users-store-py-userstore-pytest-20260408T090909`
- Created: `2026-04-08T09:09:09`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 backend/services/users/store.py，抽离共享用户行映射与用户名/显示名引用构建逻辑，保持 UserStore 读写契约和现有 pytest 行为稳定`

## Test Scope

Validate that the bounded store refactor preserves:

- `UserStore` full-name persistence and read-side mapping
- user-id/username reference lookup behavior
- shared row mapping behavior used by `get_by_username`, `get_by_user_id`, and `list_users`

Out of scope:

- router- or service-level user flows beyond the focused store tests
- broader password, session, or permission-group integration behavior
- schema migration or startup validation

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend runtime: local Python/pytest against temporary SQLite databases created by the tests
- Test runtime: focused unit tests that exercise the real `UserStore`

## Accounts and Fixtures

- tests create temporary auth databases through the existing test helpers and schema setup
- no external service, credentials, or browser runtime is required
- if `python` or `pytest` is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_user_store_full_name_mapping_unit.py backend/tests/test_user_store_full_name_unit.py backend/tests/test_user_store_username_refs_unit.py -q`
  - Expected success signal: all focused `UserStore` tests pass in one non-verbose pytest run

## Test Cases

### T1: UserStore read-side regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit
- Command: `python -m pytest backend/tests/test_user_store_full_name_mapping_unit.py backend/tests/test_user_store_full_name_unit.py backend/tests/test_user_store_username_refs_unit.py -q`
- Expected: extracted helpers preserve full-name reads and user-id/username reference lookups
  without changing current `UserStore` behavior

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend user store | shared row mapping and lookup helper extraction preserves current read behavior | unit | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused pytest command against the real repo state and the
  temporary SQLite fixtures created by the tests
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the focused pytest command succeeds
  - current `UserStore` full-name and reference-lookup behavior remains stable
- Fail when:
  - the command fails
  - helper extraction changes the expected mapping or lookup semantics

## Regression Scope

- `backend/services/users/store.py`
- new helper module(s) under `backend/services/users/`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
