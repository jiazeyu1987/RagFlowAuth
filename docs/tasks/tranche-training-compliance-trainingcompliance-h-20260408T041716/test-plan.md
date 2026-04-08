# Training Compliance Refactor Test Plan

- Task ID: `tranche-training-compliance-trainingcompliance-h-20260408T041716`
- Created: `2026-04-08T04:17:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构：以培训合规模块为下一轮 tranche，拆分后端 training_compliance 服务与前端 TrainingCompliance 页面/Hook，保持行为稳定并补齐验证。`

## Test Scope

Validate that the bounded training-compliance refactor preserves:

- backend requirement, record, certification, and authorization API behavior
- approval/data-security integration paths already covered by backend training-compliance tests
- frontend page loading, tab switching, user search, record creation, certification creation, and
  query-param prefill behavior

Out of scope:

- full end-to-end browser validation against a live backend
- redesign or accessibility restyling checks
- unrelated user-management or approval UI flows

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python pytest / unittest-compatible environment already used by repo tests
- Frontend: Node.js/npm with Jest via `react-scripts test`

## Accounts and Fixtures

- backend tests rely on existing temporary SQLite database fixtures and training qualification
  helpers
- frontend tests rely on mocked `trainingComplianceApi`, mocked `usersApi.search`, and mocked
  `useAuth`
- if either Python or npm test tooling is unavailable, fail fast and record the missing
  prerequisite

## Commands

- `python -m pytest backend/tests/test_training_compliance_api_unit.py`
  - Expected success signal: focused backend training-compliance API suite passes
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/trainingCompliance/useTrainingCompliancePage.test.js src/pages/TrainingComplianceManagement.test.js`
  - Expected success signal: focused frontend training-compliance suites pass

## Test Cases

### T1: Backend training-compliance contract regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / API integration
- Command: `python -m pytest backend/tests/test_training_compliance_api_unit.py`
- Expected: requirement/record/certification APIs and authorization gate behavior remain stable

### T2: Frontend training-compliance page regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/trainingCompliance/useTrainingCompliancePage.test.js src/pages/TrainingComplianceManagement.test.js`
- Expected: page shell, user search, form submission, and query-param prefill behavior remain
  stable

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend training compliance | service decomposition preserves API and integration behavior | unit/API integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | frontend training compliance | page/hook decomposition preserves UI interactions and prefills | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run focused backend and frontend suites against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - backend service and frontend page/hook are decomposed without breaking their current contracts
- Fail when:
  - either focused test command fails
  - API envelopes, authorization semantics, or page interactions regress

## Regression Scope

- `backend/services/training_compliance.py`
- `backend/app/modules/training_compliance/router.py`
- `backend/tests/test_training_compliance_api_unit.py`
- `fronted/src/features/trainingCompliance/*`
- `fronted/src/pages/TrainingComplianceManagement.js`
- `fronted/src/pages/TrainingComplianceManagement.test.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each suite passed.
