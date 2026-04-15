# Test Report

- Task ID: `docs-tasks-document-control-flow-parallel-202604-20260414T224329`
- Created: `2026-04-14T22:43:29`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws03-controlled-release-and-distribution.md 下的工作`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: `python`, `pytest`
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Record the tester's first-pass visibility honestly. In `blind-first-pass`, the tester should record `yes` only after writing an initial verdict before inspecting withheld artifacts.

## Results

### T1: Publish rejects without approval completion

- Result: passed
- Covers: P2-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite runtime with `ensure_schema()` and real service/router fixtures
- Evidence refs: `backend/tests/test_document_control_service_unit.py::test_publish_rejects_when_not_approved_pending_effective`
- Notes: explicit `publish_revision()` rejects non-`approved_pending_effective` revisions.

### T2: Publish enforces training gate

- Result: passed
- Covers: P2-AC2
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite runtime with `TrainingComplianceService` fixtures
- Evidence refs: `backend/tests/test_document_control_service_unit.py::test_publish_fail_fast_when_training_gate_not_configured`
- Notes: missing release-actor training record blocks publish with fail-fast error.

### T3: Publish writes ledger and makes revision effective

- Result: passed
- Covers: P1-AC1, P2-AC3
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite runtime with real schema migrations applied
- Evidence refs: `backend/tests/test_document_control_service_unit.py::test_publish_writes_release_ledger_and_supersedes_previous_effective`
- Notes: ledger rows persist publish and replacement metadata; published revision becomes `effective`.

### T4: Replacement publish supersedes previous effective revision

- Result: passed
- Covers: P1-AC2, P2-AC4
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite runtime with two revisions for the same controlled document
- Evidence refs: `backend/tests/test_document_control_service_unit.py::test_publish_writes_release_ledger_and_supersedes_previous_effective`
- Notes: previous effective revision becomes `superseded`, not lifecycle `obsolete`, and stores `superseded_*` metadata.

### T5: API flow uses explicit publish endpoint

- Result: passed
- Covers: P3-AC1, P4-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: FastAPI `TestClient` hitting document-control routes against the real service stack
- Evidence refs: `backend/tests/test_document_control_api_unit.py::test_routes_allow_kb_name_variant_and_complete_workflow_flow`
- Notes: workflow submit/approve/publish path succeeds through explicit endpoints and legacy transitions remain removed.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P2-AC1, P2-AC2, P2-AC3, P2-AC4, P3-AC1, P4-AC1
- Blocking prerequisites:
- Summary: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q` passed with 20 tests. WS03 explicit publish, release ledger, training gate enforcement, and supersede semantics are validated against the current backend contract, including existing department-distribution coupling on publish.

## Open Issues

- None yet.
