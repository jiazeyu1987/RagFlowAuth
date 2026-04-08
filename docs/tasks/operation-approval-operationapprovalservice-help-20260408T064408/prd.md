# Operation Approval Follow-up Refactor PRD

- Task ID: `operation-approval-operationapprovalservice-help-20260408T064408`
- Created: `2026-04-08T06:44:08`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：在 operation_approval 域做第二轮局部重构，继续收敛后端 OperationApprovalService 剩余共享 helper 与历史死代码，同时拆分前端审批中心/审批配置 hook 的剩余混合职责，保持现有 API、页面行为和测试契约稳定。`

## Goal

Continue the bounded operation-approval refactor so the backend service stops carrying most of the
shared helper implementation and historical dead branches after the first extraction pass, while the
frontend approval hooks stop mixing URL sync, data loading, mutation orchestration, member search,
and draft editing in the same files. Preserve the existing approval API surface, state-machine
semantics, page behaviour, and regression-test contracts.

## Scope

- `backend/services/operation_approval/service.py`
- new bounded backend helper modules under `backend/services/operation_approval/`
- `backend/services/operation_approval/action_service.py`
- `backend/services/operation_approval/query_service.py` only if support wiring changes are required
- `backend/services/operation_approval/__init__.py` only if export wiring cleanup is required
- `backend/tests/test_operation_approval_service_unit.py`
- `backend/tests/test_operation_approval_router_unit.py`
- `backend/tests/test_operation_approval_notification_migration_unit.py`
- `fronted/src/features/operationApproval/useApprovalCenterPage.js`
- `fronted/src/features/operationApproval/useApprovalConfigPage.js`
- new bounded frontend hooks/helpers/components under `fronted/src/features/operationApproval/`
- `fronted/src/features/operationApproval/useApprovalCenterPage.test.js`
- `fronted/src/features/operationApproval/useApprovalConfigPage.test.js`
- `fronted/src/pages/ApprovalCenter.js`
- `fronted/src/pages/ApprovalCenter.test.js`
- `fronted/src/pages/ApprovalConfig.js`
- `fronted/src/pages/ApprovalConfig.test.js`

## Non-Goals

- changing operation-approval API paths, response envelopes, or error-code semantics
- changing approval workflow state-machine rules, signature semantics, or handler behaviour
- changing approval page copy, interaction contracts, or existing `data-testid` selectors
- expanding into unrelated modules such as notification center, data security, document preview, or permissions
- introducing fallback branches, silent downgrades, or compatibility shims

## Preconditions

- focused backend operation-approval pytest suites run locally
- focused frontend approval hook/page Jest suites run locally
- `OperationApprovalService` remains the stable backend entry point exported through `backend/services/operation_approval/__init__.py`
- `ApprovalCenter` and `ApprovalConfig` remain the stable frontend page entries used by routing

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- backend approval request/workflow/detail helper logic shared by `action_service.py` and `query_service.py`
- backend approval artifact cleanup and execution dependency resolution
- frontend approval-center URL/query-state sync, list/detail loading, signature action handling, and withdraw flow
- frontend approval-config draft loading, configured-user hydration, member search, and workflow draft mutation helpers
- focused tests:
  - `backend/tests/test_operation_approval_service_unit.py`
  - `backend/tests/test_operation_approval_router_unit.py`
  - `backend/tests/test_operation_approval_notification_migration_unit.py`
  - `fronted/src/features/operationApproval/useApprovalCenterPage.test.js`
  - `fronted/src/features/operationApproval/useApprovalConfigPage.test.js`
  - `fronted/src/pages/ApprovalCenter.test.js`
  - `fronted/src/pages/ApprovalConfig.test.js`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: Extract backend approval support helpers and remove dead branches

- Objective:
  - move the remaining shared helper implementation out of `OperationApprovalService` and delete the
    unreachable legacy bodies that remain after the first facade extraction pass
- Owned paths:
  - `backend/services/operation_approval/service.py`
  - new helper modules under `backend/services/operation_approval/`
  - `backend/services/operation_approval/action_service.py`
  - `backend/services/operation_approval/query_service.py`
  - `backend/tests/test_operation_approval_service_unit.py`
- Dependencies:
  - existing `OperationApprovalActionService`
  - existing `OperationApprovalQueryService`
  - existing `OperationApprovalDecisionService`, execution, migration, audit, and notification services
- Deliverables:
  - slimmer `OperationApprovalService` facade with helper delegation instead of inline implementations
  - removed unreachable legacy code after delegated public methods
  - preserved public methods, imports, and behaviour for approval callers and tests

### P2: Split frontend approval hooks into focused state and action units

- Objective:
  - decompose the remaining mixed responsibilities in `useApprovalCenterPage.js` and
    `useApprovalConfigPage.js` without changing current page behaviour
- Owned paths:
  - `fronted/src/features/operationApproval/useApprovalCenterPage.js`
  - `fronted/src/features/operationApproval/useApprovalConfigPage.js`
  - new helper hooks/modules under `fronted/src/features/operationApproval/`
  - `fronted/src/pages/ApprovalCenter.js` only if wiring cleanup is required
  - `fronted/src/pages/ApprovalConfig.js` only if wiring cleanup is required
- Dependencies:
  - existing `operationApprovalApi`
  - existing `usersApi`
  - existing `useSignaturePrompt`
  - current approval hook/page tests
- Deliverables:
  - approval-center hook composed from focused query-state/data/action helpers
  - approval-config hook composed from focused data-loading, draft-editing, and member-search helpers
  - unchanged page behaviour and existing test ids

### P3: Focused validation and tranche evidence

- Objective:
  - prove the second-pass operation-approval refactor preserved backend and frontend behaviour and
    record exact evidence in task artifacts
- Owned paths:
  - `docs/tasks/operation-approval-operationapprovalservice-help-20260408T064408/*`
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused backend/frontend regression evidence
  - updated execution/test artifacts and completion-ready task state

## Phase Acceptance Criteria

### P1

- P1-AC1:
  - `OperationApprovalService` no longer directly owns most workflow normalization, request enrichment,
    user resolution, request materialization, and artifact cleanup implementation in one file.
- P1-AC2:
  - public approval service methods, router contracts, and approval state-machine behaviour remain stable.
- P1-AC3:
  - the historical dead branches that sit after delegated public-method returns are removed, reducing
    maintenance noise without changing executed behaviour.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1:
  - `useApprovalCenterPage.js` no longer directly mixes URL/query syncing, data loading, and action orchestration in one file.
- P2-AC2:
  - `useApprovalConfigPage.js` no longer directly mixes workflow loading, configured-user hydration,
    draft mutation helpers, and member-search state in one file.
- P2-AC3:
  - current approval-center and approval-config behaviours, rendered copy, and test selectors remain stable after extraction.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1:
  - focused backend and frontend approval regression commands pass against the final code state.
- P3-AC2:
  - task artifacts record changed paths, exact commands, acceptance coverage, and bounded residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- operation-approval API contracts, service exports, and approval frontend behaviour remain stable.

## Blocking Conditions

- focused backend or frontend validation cannot run
- the follow-up refactor would require changing public approval API paths, response envelopes, or state semantics
- preserving current behaviour would require fallback branches or silent downgrade
- helper extraction reveals hidden coupling that would force unrelated non-approval modules into scope
