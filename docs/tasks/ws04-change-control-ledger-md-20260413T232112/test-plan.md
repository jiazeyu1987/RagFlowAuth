# Test Plan: WS04 Change Control Ledger

- Task ID: `ws04-change-control-ledger-md-20260413T232112`
- Created: `2026-04-13T23:21:12`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成WS04-change-control-ledger.md下的工作`

## Test Scope

Validate WS04 backend workflow and frontend route/page behavior:

- backend change-control request and plan-item workflow APIs
- due reminder dispatch behavior through existing inbox structure
- cross-department confirmation and close transition
- frontend `/quality-system/change-control` interaction path

Out of scope:

- E2E browser automation
- changes to route registry or permission model internals
- unrelated quality-system modules

## Environment

- OS: Windows / PowerShell
- Backend test runner: `python -m pytest`
- Frontend test runner: `npm test` (react scripts / jest)
- Repo root: `D:\ProjectPackage\RagflowAuth`

## Accounts and Fixtures

- backend unit tests use local temp sqlite database fixture.
- frontend tests use mocked API layer and React Testing Library.

If python, pytest, npm, or frontend test runtime is missing, fail fast and record missing prerequisite.

## Commands

Run from repo root:

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth'
```

1. Backend WS04 unit tests:

```powershell
python -m pytest backend/tests/test_change_control_api_unit.py -q
```

Expected: all tests pass.

2. Frontend WS04 API tests:

```powershell
npm --prefix fronted test -- --runInBand --watch=false src/features/changeControl/api.test.js
```

Expected: all tests pass.

3. Frontend WS04 page tests:

```powershell
npm --prefix fronted test -- --runInBand --watch=false src/pages/ChangeControl.test.js
```

Expected: all tests pass.

4. Narrow regression test for quality-system host page:

```powershell
npm --prefix fronted test -- --runInBand --watch=false src/pages/QualitySystem.test.js
```

Expected: existing quality-system behavior remains valid after WS04 page integration.

## Test Cases

### T1: Create/list/get change request workflow

- Covers: P1-AC1
- Level: backend unit
- Command: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Expected: request creation/list/get pass with required validation and expected state fields.

### T2: Plan-item lifecycle and parent-state guards

- Covers: P1-AC2
- Level: backend unit
- Command: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Expected: plan items can be added/updated in valid states and rejected in invalid states.

### T3: Reminder dispatch path uses existing inbox payload

- Covers: P1-AC3
- Level: backend unit
- Command: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Expected: dispatch endpoint returns reminder count and writes inbox-compatible payload/event entries.

### T4: Cross-department confirmation and close writeback

- Covers: P1-AC4, P1-AC5
- Level: backend unit
- Command: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Expected: confirmation gate enforced; close records closure metadata and controlled revision references.

### T5: Frontend change-control API client contract

- Covers: P2-AC2
- Level: frontend unit
- Command: `npm --prefix fronted test -- --runInBand --watch=false src/features/changeControl/api.test.js`
- Expected: request helpers return normalized response shape and throw mapped errors on failure.

### T6: `/quality-system/change-control` renders WS04 page

- Covers: P2-AC1, P2-AC3
- Level: frontend unit
- Command: `npm --prefix fronted test -- --runInBand --watch=false src/pages/ChangeControl.test.js`
- Expected: page renders, supports key WS04 actions, and can display API-driven state.

### T7: QualitySystem host regression after WS04 embedding

- Covers: P3-AC2
- Level: frontend regression unit
- Command: `npm --prefix fronted test -- --runInBand --watch=false src/pages/QualitySystem.test.js`
- Expected: non-WS04 quality-system shell behavior stays valid.

### T8: Evidence and artifact completion

- Covers: P3-AC1, P3-AC2, P3-AC3
- Level: workflow/manual
- Command: review `execution-log.md` and `test-report.md` for command trace + acceptance coverage.
- Expected: every acceptance id has evidence references.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend/change_control | create/list/get workflow | backend unit | P1-AC1 | `test-report.md` |
| T2 | backend/change_control | plan-item state guards | backend unit | P1-AC2 | `test-report.md` |
| T3 | backend/change_control | reminders dispatch | backend unit | P1-AC3 | `test-report.md` |
| T4 | backend/change_control | confirmation + close writeback | backend unit | P1-AC4, P1-AC5 | `test-report.md` |
| T5 | fronted/features/changeControl | API client contract | frontend unit | P2-AC2 | `test-report.md` |
| T6 | fronted/pages/ChangeControl | WS04 page behavior | frontend unit | P2-AC1, P2-AC3 | `test-report.md` |
| T7 | fronted/pages/QualitySystem | host page regression | frontend unit | P3-AC2 | `test-report.md` |
| T8 | task artifacts | evidence completeness | manual/workflow | P3-AC1, P3-AC2, P3-AC3 | `execution-log.md`, `test-report.md` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: PowerShell, python, pytest, npm/jest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run against current repository code and generated task artifacts.
- Escalation rule: tester must record initial verdict before inspecting withheld artifacts.

## Pass / Fail Criteria

- Pass when:
  - all WS04 backend and frontend test commands pass
  - workflow transitions and reminder/confirmation/close behavior match PRD acceptance criteria
  - evidence coverage is complete for all acceptance ids
- Fail when:
  - any required test command fails
  - workflow allows invalid transitions
  - reminders/close writeback requirements are missing
  - acceptance ids are not evidenced

## Regression Scope

- `backend/services/emergency_change.py` compatibility (must remain unaffected)
- quality-system shell page rendering on non-WS04 modules
- frontend shared HTTP client contract usage for new API client

## Reporting Notes

Tester writes per-case outcomes and final verdict to `test-report.md`, including command list, result summary, and acceptance-id verification evidence.
