# Training Compliance Refactor PRD

- Task ID: `tranche-training-compliance-trainingcompliance-h-20260408T041716`
- Created: `2026-04-08T04:17:16`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构：以培训合规模块为下一轮 tranche，拆分后端 training_compliance 服务与前端 TrainingCompliance 页面/Hook，保持行为稳定并补齐验证。`

## Goal

Decompose the training-compliance backend service and frontend page/hook into smaller, more
cohesive units so that future requirement, record, certification, and authorization changes stop
accumulating in two oversized files, while preserving the current API and UI behavior.

## Scope

- `backend/services/training_compliance.py`
- new bounded backend helper modules for training-compliance validation, serialization, repository,
  and orchestration responsibilities
- `backend/app/modules/training_compliance/router.py` only if dependency wiring or adapter cleanup
  is needed
- `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js`
- `fronted/src/pages/TrainingComplianceManagement.js`
- new bounded frontend helper modules/components under `fronted/src/features/trainingCompliance/`
- focused backend and frontend tests for the training-compliance module
- `docs/exec-plans/active/training-compliance-refactor-phase-1.md`

## Non-Goals

- changing training-compliance API paths or response envelopes
- redesigning the training-compliance UI
- introducing fallback behavior for invalid payloads or missing users
- changing approval/data-security integration semantics
- refactoring unrelated user-search infrastructure outside this module

## Preconditions

- Existing backend training-compliance API tests can run.
- Existing frontend training-compliance page and hook tests can run.
- `TrainingComplianceService` remains the public backend entry point used by router wiring and
  cross-module integrations.
- `TrainingComplianceManagement` remains the page entry consumed by routing.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- backend requirement/query/write flows in `TrainingComplianceService`
- router-level user existence checks and payload mapping in
  `backend/app/modules/training_compliance/router.py`
- approval and restore-drill training authorization checks exercised through API tests
- frontend page copy, form sections, user lookup behavior, tab panels, and page-level rendering
- frontend hook responsibilities for initial loading, query-param prefills, user lookup, and form
  submission

## Phase Plan

### P1: Decompose backend training-compliance service

- Objective: Split validation, serialization, query, and mutation responsibilities out of the
  monolithic backend service while keeping `TrainingComplianceService` as the stable facade.
- Owned paths:
  - `backend/services/training_compliance.py`
  - new helper modules under `backend/services/`
  - `backend/app/modules/training_compliance/router.py` only if adapter cleanup is required
- Dependencies:
  - existing router contract
  - existing approval/data-security integrations
  - existing SQLite schema
- Deliverables:
  - slimmer backend facade
  - extracted helper modules for reusable training-compliance responsibilities
  - unchanged external service and router semantics

### P2: Decompose frontend training-compliance page and hook

- Objective: Split the page shell and hook into smaller, focused units for user lookup, form
  wiring, and tab-panel rendering without changing current page behavior.
- Owned paths:
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePage.js`
  - `fronted/src/pages/TrainingComplianceManagement.js`
  - new helper modules/components under `fronted/src/features/trainingCompliance/`
- Dependencies:
  - existing `trainingComplianceApi`
  - existing `usersApi.search`
  - current page tests and route usage
- Deliverables:
  - slimmer page component
  - extracted helper hooks/components for user search and tab sections
  - stable page-level behavior and test ids

### P3: Focused regression validation and task evidence

- Objective: Prove the bounded refactor preserved both backend and frontend training-compliance
  behavior.
- Owned paths:
  - `backend/tests/test_training_compliance_api_unit.py`
  - `fronted/src/features/trainingCompliance/useTrainingCompliancePage.test.js`
  - `fronted/src/pages/TrainingComplianceManagement.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused backend/frontend regression coverage
  - execution/test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `TrainingComplianceService` no longer directly owns all validation helpers, row
  serialization, query composition, and mutation orchestration in one file.
- P1-AC2: existing router behavior and cross-module training authorization flows remain unchanged.
- P1-AC3: training requirement, record, certification, and authorization logic still fails fast on
  invalid or missing prerequisites.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `TrainingComplianceManagement.js` no longer mixes page shell, local copy/config,
  reusable lookup widget, and both record/certification panel render trees in one file.
- P2-AC2: `useTrainingCompliancePage.js` no longer directly owns all duplicated user-search effect
  logic and page-form orchestration in one file.
- P2-AC3: current page interactions, test ids, and query-param prefills remain stable after
  extraction.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused backend and frontend training-compliance tests pass against the final code state.
- P3-AC2: task artifacts record the exact commands run, verified acceptance coverage, and any
  bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- The training-compliance router, service facade, page contract, and key UI interactions remain
  stable.

## Blocking Conditions

- focused backend or frontend validation cannot run
- refactor would require changing public API paths or envelopes
- preserving current behavior would require fallback branches or silent downgrades
- helper extraction would break existing approval or restore-drill training gate semantics
