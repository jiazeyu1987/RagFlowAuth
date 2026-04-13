# Test Report

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173942`
- Created: `2026-04-13T17:39:42`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS01-controlled-doc-baseline.md 开发 WS01 受控文件基线与合规门禁`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: pytest, npm (react-scripts test)
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: 受控文件主档与修订创建

- Result: passed
- Covers: P1-AC1
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py -q`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth` with repository test fixtures.
- Evidence refs: `execution-log.md#Phase-P1`
- Notes: document control service tests passed and persisted required metadata fields.

### T2: 生命周期与单现行版本约束

- Result: passed
- Covers: P1-AC2, P1-AC3
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth` against isolated SQLite fixtures.
- Evidence refs: `execution-log.md#Phase-P1`
- Notes: transition constraints, single-effective behavior, and effective/obsolete audit events were validated.

### T3: 审核包与统一受控根

- Result: passed
- Covers: P1-AC4, P1-AC5
- Command run: `python -m pytest backend/tests/test_compliance_review_package_api_unit.py backend/tests/test_gbz02_compliance_gate_unit.py backend/tests/test_gbz04_compliance_gate_unit.py backend/tests/test_gbz05_compliance_gate_unit.py -q`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth` using temp repo fixtures with `doc/compliance/*`.
- Evidence refs: `execution-log.md#Phase-P1`
- Notes: review package export and GBZ gates resolved compliance content through one controlled-root path.

### T4: 既有文档版本链不回归

- Result: passed
- Covers: P1-AC1, P1-AC2
- Command run: `python -m pytest backend/tests/test_document_versioning_unit.py backend/tests/test_knowledge_ingestion_manager_unit.py -q`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth` outside sandbox after sandbox temp-dir permission denials.
- Evidence refs: `execution-log.md#Phase-P1`
- Notes: outside-sandbox rerun passed (`12 passed`) with no code changes, confirming regression scope behavior.

### T5: 前端页面筛选与详情

- Result: passed
- Covers: P2-AC1, P2-AC3
- Command run: `npm test -- --runInBand --watchAll=false src/features/documentControl src/pages/DocumentControl.test.js`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth\fronted` via `react-scripts test`.
- Evidence refs: `execution-log.md#Phase-P2`
- Notes: page renders controlled-document list, filter behavior, and revision detail flow.

### T6: 前端状态操作与错误处理

- Result: passed
- Covers: P2-AC2, P2-AC4
- Command run: `npm test -- --runInBand --watchAll=false src/features/documentControl src/pages/DocumentControl.test.js`
- Environment proof: executed in `D:\ProjectPackage\RagflowAuth\fronted` with mocked API responses for success/failure branches.
- Evidence refs: `execution-log.md#Phase-P2`
- Notes: create/transition actions and failure handling are covered in frontend tests.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Blocking prerequisites:
- Summary: WS01 backend and frontend scopes both validated; lifecycle, single-root compliance alignment, and document-control UI behavior all passed planned checks.

## Open Issues

- None yet.
