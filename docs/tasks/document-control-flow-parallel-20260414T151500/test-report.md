# Test Report

- Task ID: `document-control-flow-parallel-20260414T151500`
- Created: `2026-04-14T20:50:21`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `把文件控制流程初稿与当前系统差异，细化成可由不同 LLM 并行执行的独立工作文件`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-runtime
- Tools: `python`, `pytest`, `react-scripts test`
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

## Results

### T1: Approval workflow replaces direct transitions

- Result: passed
- Covers: P1-AC1, P1-AC2
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite-backed backend unit/API runtime
- Evidence refs: `backend/services/document_control/service.py`, `backend/app/modules/document_control/router.py`, `backend/tests/test_document_control_service_unit.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: approval submission, cosign, approve, standardize review, reject/resubmit, and add-sign are exercised through the workflow-based API.
- Notes: approval submission, cosign, approve, standardize review, reject/resubmit, add-sign, and document-type workflow persistence are exercised through the workflow-based API.

### T2: Training gate blocks publish until satisfied

- Result: passed
- Covers: P2-AC1, P2-AC2
- Command run: `python -m pytest backend/tests/test_training_compliance_api_unit.py backend/tests/test_document_control_service_unit.py -q`
- Environment proof: local SQLite-backed backend unit/API runtime
- Evidence refs: `backend/services/training_compliance.py`, `backend/app/modules/training_compliance/router.py`, `backend/database/schema/training_ack.py`, `backend/tests/test_training_compliance_api_unit.py`, `backend/tests/test_document_control_service_unit.py`
- Notes: trainable revisions support explicit assignees or departments, training gate must be explicitly configured, question resolution reopens acknowledgment, and publish is blocked when the revision gate is still blocking.

### T3: Publish and release ledger are explicit

- Result: passed
- Covers: P3-AC1, P3-AC2
- Command run: `python -m pytest backend/tests/test_document_control_service_unit.py backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite-backed backend unit/API runtime
- Evidence refs: `backend/services/document_control/service.py`, `backend/database/schema/document_control.py`, `backend/tests/test_document_control_service_unit.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: publish uses explicit endpoints, validates prerequisites, and writes release/supersede ledger entries.

### T4: Department acknowledgment uses document-control APIs

- Result: passed
- Covers: P4-AC1, P4-AC2
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py -q`
- Environment proof: local SQLite-backed backend API runtime with notification fixtures
- Evidence refs: `backend/app/modules/document_control/router.py`, `backend/services/document_control/service.py`, `backend/services/notification/event_catalog.py`, `backend/services/notification/code_defaults.py`, `backend/tests/test_document_control_api_unit.py`
- Notes: department acknowledgments are created after publish, confirmed via document-control endpoints, approval-step overdue reminders execute through the document-control reminder endpoint, and both reminder paths emit document-control notification events.

### T5: Obsolete, retention, and destruction remain controlled

- Result: passed
- Covers: P5-AC1, P5-AC2
- Command run: `python -m pytest backend/tests/test_document_control_api_unit.py backend/tests/test_retired_document_access_unit.py -q`
- Environment proof: local SQLite-backed backend runtime with archived-record fixtures
- Evidence refs: `backend/services/compliance/retired_records.py`, `backend/services/document_control/service.py`, `docs/compliance/release_and_retirement_sop.md`, `docs/compliance/retirement_plan.md`, `backend/tests/test_document_control_api_unit.py`, `backend/tests/test_retired_document_access_unit.py`
- Notes: obsolete initiation/approval is explicit, retention access is controlled, expired archived records are purged automatically on access/list paths, and destruction records are written for obsolete controlled revisions.

### T6: Frontend workspace uses real document-control APIs

- Result: passed
- Covers: P6-AC1, P6-AC2
- Command run: `npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js api.test.js userFacingErrorMessages.test.js trainingCompliance/api.test.js`
- Environment proof: local Jest + React Testing Library runtime
- Evidence refs: `fronted/src/features/documentControl/api.js`, `fronted/src/features/documentControl/useDocumentControlPage.js`, `fronted/src/pages/DocumentControl.js`, `fronted/src/features/trainingCompliance/api.js`, `fronted/src/shared/errors/userFacingErrorMessages.js`, `fronted/src/features/documentControl/api.test.js`, `fronted/src/features/documentControl/useDocumentControlPage.test.js`, `fronted/src/pages/DocumentControl.test.js`, `fronted/src/features/trainingCompliance/api.test.js`
- Notes: frontend no longer exposes direct status transitions and now wires training gate, publish, approval-overdue reminder, distribution, acknowledgment, obsolete, and destruction actions to the document-control API surface.

### T7: Real-browser PDF flow walkthrough

- Result: passed
- Covers: P1-AC1, P1-AC2, P2-AC1, P2-AC2, P3-AC1, P3-AC2, P4-AC1, P4-AC2, P5-AC1, P5-AC2, P6-AC1, P6-AC2
- Command run: `cd D:\ProjectPackage\RagflowAuth\fronted && npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-pdf-flow.spec.js --project=chromium --workers=1`
- Environment proof: real browser + isolated doc E2E backend/frontend runtime booted from `fronted/playwright.docs.config.js`; not the production server
- Evidence refs: `fronted/e2e/tests/docs.document-control-pdf-flow.spec.js`, `output/playwright/document-control-pdf-flow/videos/b229ca440fb70e7b8cee7a32cc76c958.webm`, `output/playwright/document-control-pdf-flow/videos/7d072b8f73de324347213332c0b6405a.webm`, `docs/tasks/document-control-flow-parallel-20260414T151500/pdf-flow-e2e-uat.md`
- Notes: this walkthrough uses the desktop PDF as the real upload source, covers document-type workflow resolution, approval overdue reminder, training gate blocking/unblocking, automatic/manual release behavior, department acknowledgment, obsolete approval, and destruction confirmation.

### T8: Branch coverage for reject-resubmit and question resolution

- Result: passed
- Covers: P1-AC1, P1-AC2, P2-AC1, P2-AC2, P3-AC1
- Command run: `cd D:\ProjectPackage\RagflowAuth\fronted && npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-branch-coverage.spec.js --project=chromium --workers=1`
- Environment proof: real browser + isolated doc E2E backend/frontend runtime booted from `fronted/playwright.docs.config.js`; not the production server
- Evidence refs: `fronted/e2e/tests/docs.document-control-branch-coverage.spec.js`
- Notes: covers document-control rejection followed by resubmission on the same revision, then exercises the training question branch (`questioned -> resolve -> re-acknowledge`) before final publish.

### T9: Add-sign and automatic scheduler reminder branches

- Result: passed
- Covers: P1-AC1, P1-AC2, P4-AC2
- Command run: `cd D:\ProjectPackage\RagflowAuth\fronted && $env:DOCUMENT_CONTROL_SCHEDULER_INTERVAL_SECONDS='5'; npx playwright test --config playwright.docs.config.js e2e/tests/docs.document-control-edge-branches.spec.js --project=chromium --workers=1`
- Environment proof: real browser + isolated doc E2E backend/frontend runtime with accelerated document-control scheduler interval; not the production server
- Evidence refs: `fronted/e2e/tests/docs.document-control-edge-branches.spec.js`, `backend/services/document_control_scheduler.py`
- Notes: covers UI-driven add-sign plus proof that the added approver must participate before step advancement, and validates that the backend scheduler can automatically mark approval reminders as overdue without a manual reminder click.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P2-AC1, P2-AC2, P3-AC1, P3-AC2, P4-AC1, P4-AC2, P5-AC1, P5-AC2, P6-AC1, P6-AC2
- Summary: The integrated implementation now matches the intended approval, document-type workflow, training, publish, approval-overdue reminder, department-acknowledgment, add-sign, obsolete-retention, retention-expiry cleanup, and PDF-only upload flow, and targeted unit coverage plus real-browser main-flow and branch-flow walkthroughs pass in the isolated E2E runtime.

## Open Issues

- None.
