# Test Report

- Task ID: `ws04-change-control-ledger-md-20260413T232112`
- Created: `2026-04-13T23:21:12`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成WS04-change-control-ledger.md下的工作`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: PowerShell, python, pytest, npm/react-scripts(jest)
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: Create/list/get change request workflow

- Result: passed
- Covers: P1-AC1
- Command run: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Environment proof: local temp sqlite db created by unit tests
- Evidence refs: `backend/tests/test_change_control_api_unit.py`, `test-report.md#T1-create-list-get-change-request-workflow`
- Notes: workflow API creation and retrieval assertions passed.

### T2: Plan-item lifecycle and parent-state guards

- Result: passed
- Covers: P1-AC2
- Command run: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Environment proof: same unit-test runtime and fixture db
- Evidence refs: `backend/tests/test_change_control_api_unit.py`, `test-report.md#T2-plan-item-lifecycle-and-parent-state-guards`
- Notes: plan item operations and invalid transition guard assertions passed.

### T3: Reminder dispatch path uses existing inbox payload

- Result: passed
- Covers: P1-AC3
- Command run: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Environment proof: inbox store/service fixture in backend unit tests
- Evidence refs: `backend/tests/test_change_control_api_unit.py`, `test-report.md#T3-reminder-dispatch-path-uses-existing-inbox-payload`
- Notes: reminder dispatch created inbox entries with `change_control_due_soon` event type.

### T4: Cross-department confirmation and close writeback

- Result: passed
- Covers: P1-AC4, P1-AC5
- Command run: `python -m pytest backend/tests/test_change_control_api_unit.py -q`
- Environment proof: same backend unit-test runtime with role-specific test users
- Evidence refs: `backend/tests/test_change_control_api_unit.py`, `test-report.md#T4-cross-department-confirmation-and-close-writeback`
- Notes: confirmation gating and close writeback fields verified.

### T5: Frontend change-control API client contract

- Result: passed
- Covers: P2-AC2
- Command run: `npm --prefix fronted test -- --runInBand --watch=false src/features/changeControl/api.test.js`
- Environment proof: fronted jest runtime
- Evidence refs: `fronted/src/features/changeControl/api.test.js`, `test-report.md#T5-frontend-change-control-api-client-contract`
- Notes: API client methods and payload normalization passed.

### T6: `/quality-system/change-control` renders WS04 page

- Result: passed
- Covers: P2-AC1, P2-AC3
- Command run: `npm --prefix fronted test -- --runInBand --watch=false src/pages/ChangeControl.test.js`
- Environment proof: fronted jest + RTL runtime
- Evidence refs: `fronted/src/pages/ChangeControl.test.js`, `test-report.md#T6-quality-systemchange-control-renders-ws04-page`
- Notes: page rendering and key workflow action wiring passed.

### T7: QualitySystem host regression after WS04 embedding

- Result: passed
- Covers: P3-AC2
- Command run: `npm --prefix fronted test -- --runInBand --watch=false src/pages/QualitySystem.test.js`
- Environment proof: fronted jest + MemoryRouter runtime
- Evidence refs: `fronted/src/pages/QualitySystem.test.js`, `test-report.md#T7-qualitysystem-host-regression-after-ws04-embedding`
- Notes: existing shell behavior remained valid; new WS04 subroute render test passed.

### T8: Evidence and artifact completion

- Result: passed
- Covers: P3-AC1, P3-AC2, P3-AC3
- Command run: artifact review + completion scripts
- Environment proof: task artifact files in `docs/tasks/ws04-change-control-ledger-md-20260413T232112/`
- Evidence refs: `execution-log.md`, `test-report.md`, `task-state.json`
- Notes: acceptance-id evidence traceability completed.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2, P3-AC3
- Blocking prerequisites:
- Summary: WS04 backend/frontend implementation and scoped regression checks passed with acceptance coverage evidence.

## Open Issues

- None.
