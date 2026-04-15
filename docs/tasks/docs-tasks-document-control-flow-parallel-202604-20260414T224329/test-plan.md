# WS03 Test Plan: Controlled Release And Distribution Ledger

- Task ID: `docs-tasks-document-control-flow-parallel-202604-20260414T224329`
- Created: `2026-04-14T22:43:29`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `完成 docs/tasks/document-control-flow-parallel-20260414T151500/prompt-ws03-controlled-release-and-distribution.md 下的工作`

## Test Scope

Validate that document control revisions can only be made effective via an explicit publish action that:

- requires approval completion (`approved_pending_effective`)
- enforces the training gate (fail fast; no bypass)
- writes a release ledger record
- supersedes (not lifecycle-obsoletes) the previous effective revision when replaced

Out of scope:

- Training assignment / acknowledgment workflow behavior (WS02)
- Department acknowledgment/distribution confirmations (WS04)
- Obsolete/retention/destruction policy (WS05)
- Frontend wiring (WS06)

## Environment

- Platform: Windows
- DB: SQLite via `ensure_schema()`
- Required services in deps (tests must construct them explicitly):
  - `training_compliance_service`
  - `user_store`
  - `document_control_approval_matrix`

Fail fast if any prerequisite is missing.

## Accounts and Fixtures

- Applicant (submitter): `reviewer-1` (must differ from approver)
- Approver: `approver-1` (approves all workflow steps in the configured test matrix)
- Publisher / doc-control operator: `docctrl-1`
  - role_code must have a configured training requirement for `controlled_action="document_review"`
  - must have passing training record + active certification

## Commands

### Primary validation

```powershell
python -m pytest `
  backend/tests/test_document_control_service_unit.py `
  backend/tests/test_document_control_api_unit.py -q
```

Expected success signal: pytest exits 0.

## Test Cases

Use stable test case ids.

### T1: Publish rejects without approval completion

- Covers: P2-AC1
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: publish returns `409`-style error (`DocumentControlError`) when revision is not `approved_pending_effective`.

### T2: Publish enforces training gate (no bypass)

- Covers: P2-AC2
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: missing training requirements blocks publish; configured + satisfied training allows publish.

### T3: Publish writes release ledger + makes revision effective

- Covers: P1-AC1, P2-AC3
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: release ledger row exists with correct mode + actor + target revision; revision becomes `effective` with `effective_at_ms` set.

### T4: Publishing new revision supersedes previous effective revision

- Covers: P1-AC2, P2-AC4
- Level: unit
- Command: `python -m pytest backend/tests/test_document_control_service_unit.py -q`
- Expected: previous effective revision becomes `superseded` (not `obsolete`), supersede metadata fields are populated, and the release ledger contains a supersede record.

### T5: API end-to-end flow uses explicit endpoints (no legacy transitions)

- Covers: P3-AC1, P4-AC1
- Level: API unit (FastAPI TestClient)
- Command: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Expected: submit/approve/publish succeed via explicit endpoints and the final document has an effective revision (no legacy transitions path).

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | service | reject publish when not approved | unit | P2-AC1 | pytest output |
| T2 | service | training gate blocks publish | unit | P2-AC2 | pytest output |
| T3 | schema+service | release ledger written on publish | unit | P1-AC1, P2-AC3 | pytest output + DB assertions |
| T4 | service | supersede semantics on replacement | unit | P2-AC4 | pytest output + DB assertions |
| T5 | router | explicit endpoints flow | api unit | P3-AC1, P4-AC1 | pytest output |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo checkout; do not mock success paths or skip gates.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly requests discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - all test cases T1–T5 pass
  - pytest command exits 0
- Fail when:
  - any acceptance criterion cannot be validated due to missing prerequisites or failing tests

## Regression Scope

- Document control listing/detail payloads that include revision fields (because revision model fields change)
- Any code that assumes replaced effective revisions are `obsolete`

## Reporting Notes

Write results to `test-report.md` with:

- commands executed
- pass/fail verdict
- any evidence references (logs, output snippets)
