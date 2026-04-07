# Org Directory Rebuild Refactor Test Plan

- Created: `2026-04-07T11:32:45`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- Request Summary: continue the repository refactor with a narrow focus on org-directory Excel rebuild logic and store-boundary cleanup.

## Test Scope

- Validate the org-directory rebuild refactor in `backend/services/org_directory/`.
- Validate that Excel parsing, rebuild persistence, and audit logging still produce the same observable behavior after the split.
- Keep frontend work and broader dependency-assembly refactors out of scope.

## Environment

- Python 3.12 on Windows with repository dependencies already installed.
- Local SQLite auth databases initialized by `backend.database.schema.ensure.ensure_schema`.
- Real repository Excel fixtures and temporary `.xlsx` workbooks created by the existing tests.
- If unittest execution, Excel fixture access, or schema initialization fails, stop and record the exact blocker in `task-state.json`.

## Accounts and Fixtures

- Temporary auth database fixture created in `backend/tests/test_org_structure_manager_unit.py`.
- Repository Excel fixture resolved through `OrgStructureManager.excel_path`.
- Temporary workbook uploads created by `openpyxl.Workbook`.
- API test admin fixture from `backend/tests/test_org_directory_api_unit.py`.

## Commands

- `python -m unittest backend.tests.test_org_structure_manager_unit`
  Expected success signal: all manager rebuild tests pass and the command ends with `OK`.
- `python -m unittest backend.tests.test_org_directory_api_unit`
  Expected success signal: all org-directory API regression tests pass and the command ends with `OK`.

## Test Cases

### T1: Rebuild Persistence Regression

- Covers: P1-AC1, P1-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_org_structure_manager_unit`
- Expected: rebuild still creates stable ids, clears stale user references, and preserves rebuild summary behavior while manager orchestration no longer reaches through private store internals.

### T2: Excel Parser Regression

- Covers: P1-AC2, P1-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_org_structure_manager_unit`
- Expected: duplicate employee ids, `.xlsx` uploads, header validation, and normalized parsed records continue to behave the same through the extracted parser path.

### T3: API Compatibility Regression

- Covers: P1-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_org_directory_api_unit`
- Expected: `/api/org/rebuild-from-excel`, `/api/org/tree`, `/api/org/departments`, and managed-by-Excel guardrails keep their previous behavior after the refactor.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | rebuild persistence | rebuild summary, stable ids, stale-ref cleanup, store-boundary regression | unit | P1-AC1, P1-AC3 | `execution-log.md#phase-p1`, `test-report.md#test-cycle-2026-04-07-org-directory` |
| T2 | excel parsing | parser extraction keeps validation and parsed output stable | unit | P1-AC2, P1-AC3 | `execution-log.md#phase-p1`, `test-report.md#test-cycle-2026-04-07-org-directory` |
| T3 | org API | router and API behavior remain unchanged | unit | P1-AC3 | `test-report.md#test-cycle-2026-04-07-org-directory` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, unittest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run the current working tree against the real repository tests and local SQLite-backed fixtures. Do not replace missing prerequisites with fallback paths, mocks, or assumed success.
- Escalation rule: If a required command or fixture cannot be executed from the repository context, stop immediately and record the exact blocker in `test-report.md`.

## Pass / Fail Criteria

- Pass when both org-directory test commands complete successfully and the extracted collaborators preserve rebuild and API behavior.
- Fail when parser validation changes unexpectedly, rebuild persistence changes observable results, or API behavior regresses.

## Regression Scope

- Rebuild summary counts and stable IDs.
- Stale company, department, employee, and user-reference cleanup.
- Audit-log creation for org rebuilds.
- API responses and managed-by-Excel guards in the org router.

## Reporting Notes

- Record concrete command outputs and acceptance coverage in `test-report.md`.
- The tester must remain independent from execution evidence on the first pass and should only inspect withheld artifacts after recording an initial verdict.
