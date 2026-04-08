# Users Manager Refactor PRD

- Task ID: `tranche-backend-services-users-manager-py-create-20260408T075138`
- Created: `2026-04-08T07:51:38`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：本 tranche 聚焦 backend/services/users/manager.py，抽离 create/update 共用的用户组织、角色、权限组与禁用策略解析逻辑，保持用户管理对外行为和现有单测契约稳定`

## Goal

Decompose the shared rule parsing inside `UserManagementManager` so organization validation,
manager/sub-admin assignment, permission-group resolution, and disable-policy handling stop being
duplicated across `create_user` and `update_user`, while preserving the existing business errors and
response behavior.

## Scope

- `backend/services/users/manager.py`
- new bounded backend helper module(s) under `backend/services/users/`
- focused tests:
  - `backend/tests/test_users_manager_create_duplicate_unit.py`
  - `backend/tests/test_users_manager_manager_user_unit.py`
  - `backend/tests/test_users_manager_admin_guard.py`
  - `backend/tests/test_users_manager_disable_schedule_unit.py`
- task artifacts under
  `docs/tasks/tranche-backend-services-users-manager-py-create-20260408T075138/`

## Non-Goals

- changing user API paths, payload shapes, or response models
- redesigning permission semantics for viewer, sub-admin, or admin roles
- changing persistence schemas or the users store contract
- refactoring unrelated password, alert, or auth modules
- introducing fallback or silent downgrade behavior for invalid user mutations

## Preconditions

- Python environment can run focused pytest and `py_compile`.
- `UserManagementManager` remains the public domain entry point.
- Existing users-manager tests remain the source of truth for current behavior.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- create-user organization and manager validation
- update-user organization and manager validation
- viewer/sub-admin managed-root behavior
- permission-group resolution for create/update flows
- builtin-admin disable guard and disable-schedule behavior

## Phase Plan

### P1: Extract shared user mutation rule parsing

- Objective: Move repeated create/update normalization and validation logic into bounded helpers while
  keeping `UserManagementManager` as the stable facade.
- Owned paths:
  - `backend/services/users/manager.py`
  - new helper module(s) under `backend/services/users/`
- Dependencies:
  - existing `UsersPort` contract
  - current `UserCreate`, `UserUpdate`, and `UserResponse` models
  - current business error codes asserted by tests
- Deliverables:
  - slimmer users manager facade
  - extracted shared helpers for create/update mutation preparation
  - unchanged public manager behavior

### P2: Focused backend regression validation and task evidence

- Objective: Prove the bounded users-manager refactor preserved the current business behavior.
- Owned paths:
  - focused tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - focused backend regression coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `UserManagementManager` no longer directly owns duplicated create/update parsing for
  company/department relation checks, manager/sub-admin assignment, permission-group resolution, and
  managed-root handling in one file.
- P1-AC2: existing business errors and role-specific behavior remain stable for duplicate usernames,
  manager validation, admin disable guards, and disable scheduling.
- P1-AC3: invalid user mutations still fail fast with the existing business errors instead of
  introducing fallback paths.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused users-manager tests pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `UserManagementManager` remains the stable public entry point for user domain operations.

## Blocking Conditions

- focused backend validation cannot run
- preserving current behavior would require changing public models, store contracts, or business
  error codes
- helper extraction would require fallback or silent downgrade behavior
