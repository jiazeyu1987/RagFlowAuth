# Org Directory Refactor Test Plan

- Task ID: `tranche-org-directory-orgdirectory-h-20260408T050500`
- Created: `2026-04-08T04:49:24`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勶細浠ヤ笅涓€ tranche 鑱氱劍 org directory 妯″潡锛屾媶鍒嗗悗绔?org_directory rebuild/tree 閫昏緫涓庡墠绔?OrgDirectoryManagement 椤甸潰鍜?hook锛屼繚鎸佽涓虹ǔ瀹氬苟琛ラ綈楠岃瘉銆俙`

## Test Scope

Validate that the bounded org-directory refactor preserves:

- backend org rebuild, stable-id rebuild, stale cleanup, and tree projection behavior
- org-directory router behavior already covered by API tests
- frontend page loading, search result selection, overview/audit rendering, Excel upload
  validation, and rebuild workflow behavior

Out of scope:

- full live-browser validation against a running backend
- redesign or accessibility restyling checks
- unrelated notification, user, or permission-management flows outside the org rebuild hook path

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python pytest / unittest-compatible environment already used by repo tests
- Frontend: Node.js/npm with Jest via `react-scripts test`

## Accounts and Fixtures

- backend tests rely on temporary SQLite fixtures and the repo’s org-directory Excel sample/parser
- frontend tests rely on mocked `orgDirectoryApi` and mocked `notificationApi`
- if either Python or npm tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_org_directory_api_unit.py backend/tests/test_org_structure_manager_unit.py`
  - Expected success signal: focused backend org-directory suites pass
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/orgDirectory/useOrgDirectoryManagementPage.test.js src/pages/OrgDirectoryManagement.test.js`
  - Expected success signal: focused frontend org-directory suites pass

## Test Cases

### T1: Backend org-directory contract regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / API integration
- Command: `python -m pytest backend/tests/test_org_directory_api_unit.py backend/tests/test_org_structure_manager_unit.py`
- Expected: rebuild summaries, tree shape, stable-id rebuild behavior, and router contracts remain stable

### T2: Frontend org-directory page regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/orgDirectory/useOrgDirectoryManagementPage.test.js src/pages/OrgDirectoryManagement.test.js`
- Expected: page shell, search behavior, selected-person rendering, rebuild flow, and audit panel behavior remain stable

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend org directory | manager/rebuild decomposition preserves rebuild, tree, and API behavior | unit/API integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | frontend org directory | page/hook decomposition preserves page interactions and rebuild flow | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run focused backend and frontend suites against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial verdict

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - backend org-directory facade and frontend page/hook are decomposed without breaking current contracts
- Fail when:
  - either focused test command fails
  - rebuild summaries, tree shape, router behavior, or page interactions regress

## Regression Scope

- `backend/services/org_directory/*`
- `backend/app/modules/org_directory/router.py`
- `backend/tests/test_org_directory_api_unit.py`
- `backend/tests/test_org_structure_manager_unit.py`
- `fronted/src/features/orgDirectory/*`
- `fronted/src/pages/OrgDirectoryManagement.js`
- `fronted/src/pages/OrgDirectoryManagement.test.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each suite passed.
