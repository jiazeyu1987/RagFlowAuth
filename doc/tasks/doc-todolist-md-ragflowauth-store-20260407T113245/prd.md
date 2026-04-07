# Org Directory Rebuild Refactor PRD

- Created: `2026-04-07T11:32:45`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Request Summary: continue the repository refactor with a narrow focus on org-directory Excel rebuild logic and store-boundary cleanup.

## Goal

Refactor `backend/services/org_directory/manager.py` so the Excel rebuild flow is easier to reason about and safer to maintain without changing the external org-directory API behavior. The manager should stop reaching through private store methods for transaction control and audit logging, while Excel parsing and rebuild persistence move into explicit collaborators.

## Scope

- `backend/services/org_directory/manager.py`
- `backend/services/org_directory/store.py`
- new org-directory collaborator modules under `backend/services/org_directory/`
- `backend/tests/test_org_structure_manager_unit.py`
- `backend/tests/test_org_directory_api_unit.py`

## Non-Goals

- No changes to org-directory HTTP routes or response payloads.
- No changes to the Excel file contract, required headers, or managed-by-Excel policy.
- No frontend org-directory work in this task.
- No fallback parser, compatibility shim, or silent downgrade.

## Preconditions

- Python dependencies for `openpyxl` and `xlrd` must already be installed.
- The backend auth schema must be creatable through `backend.database.schema.ensure.ensure_schema`.
- The repository fixture Excel file and temporary workbook creation used by current tests must remain readable and writable.
- If any prerequisite is missing, stop immediately and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- Org structure rebuild path used by `OrgStructureManager.rebuild_from_excel`.
- Excel parsing helpers used by manager unit tests.
- Persistence and audit-log writes against `companies`, `departments`, `org_employees`, `users`, and `org_directory_audit_logs`.
- Backend unit tests and API tests for org-directory rebuild behavior.

## Phase Plan

### P1: Extract Org Rebuild Collaborators

- Objective: Split Excel parsing and rebuild persistence out of `OrgStructureManager`, and replace private-store reach-through with explicit store APIs while preserving current rebuild behavior.
- Owned paths: `backend/services/org_directory/manager.py`, `backend/services/org_directory/store.py`, `backend/services/org_directory/*.py`, `backend/tests/test_org_structure_manager_unit.py`, `backend/tests/test_org_directory_api_unit.py`
- Dependencies: Existing org-directory unit and API tests, current Excel import fixture, and current database schema.
- Deliverables: explicit Excel parser collaborator, explicit rebuild repository/store entrypoint, manager orchestration layer that no longer calls `_get_connection` or `_log`, and passing org-directory regression tests.

## Phase Acceptance Criteria

### P1

- P1-AC1: `OrgStructureManager.rebuild_from_excel` no longer calls `self._store._get_connection()` or `self._store._log()` directly.
- P1-AC2: Excel parsing is moved behind an explicit collaborator or helper module so header validation and row normalization are no longer buried in the manager hot path.
- P1-AC3: Existing org-directory rebuild unit tests and API tests continue to pass after the refactor.
- Evidence expectation: `execution-log.md` records the extracted collaborators, the store boundary change, and the exact validation commands run.

## Done Definition

- The org-directory rebuild flow is split into orchestration plus explicit parser/persistence collaborators.
- `OrgStructureManager` preserves existing behavior and API semantics.
- The manager no longer depends on private store methods for rebuild persistence.
- `backend.tests.test_org_structure_manager_unit` and `backend.tests.test_org_directory_api_unit` pass and are recorded in task artifacts.
- Every acceptance id has evidence in `execution-log.md` or `test-report.md`.

## Blocking Conditions

- Org-directory tests cannot run in the current environment.
- The Excel fixture or auth schema cannot be initialized locally.
- The refactor would require changing the public API contract or adding fallback behavior to keep old paths working.
