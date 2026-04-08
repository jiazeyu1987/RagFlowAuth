# User Store Refactor PRD

- Task ID: `backend-services-users-store-py-userstore-pytest-20260408T090909`
- Created: `2026-04-08T09:09:09`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `聚焦 backend/services/users/store.py，抽离共享用户行映射与用户名/显示名引用构建逻辑，保持 UserStore 读写契约和现有 pytest 行为稳定`

## Goal

Decompose the duplicated read-side logic inside `backend/services/users/store.py` so the store no
longer repeats the same user-row mapping and identifier/display-name reference-building logic
across multiple methods, while preserving the existing `UserStore` read/write contract.

## Scope

- `backend/services/users/store.py`
- new bounded helper module(s) under `backend/services/users/`
- focused backend tests:
  - `backend/tests/test_user_store_full_name_mapping_unit.py`
  - `backend/tests/test_user_store_full_name_unit.py`
  - `backend/tests/test_user_store_username_refs_unit.py`
- task artifacts under
  `docs/tasks/backend-services-users-store-py-userstore-pytest-20260408T090909/`

## Non-Goals

- changing SQLite schema, table ownership, or transaction behavior
- changing `UserStore` method signatures or write-path behavior
- changing password, lockout, or permission-group semantics
- broad refactors of repo, router, or service layers outside `UserStore`

## Preconditions

- focused backend pytest can run locally
- `UserStore` remains the stable repository-layer entry point for user persistence
- existing backend tests listed above remain the source of truth for current read-side behavior

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- `get_by_username`, `get_by_user_id`, and `list_users` row-to-`User` mapping
- username and display-name lookup helpers used by surrounding user flows
- focused `UserStore` pytest coverage for full-name and username/display-name lookups

## Phase Plan

### P1: Extract shared UserStore read-side helpers

- Objective: Move repeated user-row mapping and identifier/display-name lookup logic into bounded
  local helpers while keeping `UserStore` behavior stable.
- Owned paths:
  - `backend/services/users/store.py`
  - new helper module(s) under `backend/services/users/`
- Dependencies:
  - existing `User` model
  - current SQLite schema and `user_permission_groups` reads
- Deliverables:
  - slimmer `UserStore` read methods
  - shared helper(s) for row mapping and lookup-map construction
  - unchanged `UserStore` contracts

### P2: Focused backend regression validation and tranche evidence

- Objective: Prove the bounded store refactor preserves current user-store behavior and record
  reviewable evidence.
- Owned paths:
  - focused backend tests listed above
  - task artifacts for this tranche
- Dependencies:
  - P1 completed
- Deliverables:
  - passing focused pytest coverage
  - execution and test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `store.py` no longer duplicates the same user-row-to-`User` mapping logic across the main
  read methods.
- P1-AC2: username and display-name reference maps are built through shared bounded helpers instead
  of repeated ad hoc loops.
- P1-AC3: `UserStore` read and write contracts remain stable and do not introduce fallback or silent
  downgrade behavior.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: focused `UserStore` pytest suites pass against the final code state.
- P2-AC2: task artifacts record the exact commands run, changed paths, verified acceptance ids, and
  bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T1`

## Done Definition

- P1 and P2 are completed.
- All acceptance ids are backed by evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- `UserStore` remains the stable persistence contract used by surrounding user flows.

## Blocking Conditions

- focused backend validation cannot run
- preserving current behavior would require changing `UserStore` method signatures or write-path
  semantics
- extracting helpers would require fallback branches or silent downgrade behavior
