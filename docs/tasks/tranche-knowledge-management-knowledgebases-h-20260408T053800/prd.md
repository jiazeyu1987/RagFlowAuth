# Knowledge Management Refactor PRD

- Task ID: `tranche-knowledge-management-knowledgebases-h-20260408T053800`
- Created: `2026-04-08T05:33:43`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构：以下一 tranche 聚焦 knowledge management 模块，拆分后端 KnowledgeManagementManager 与前端 KnowledgeBases 页面和 hook，保持知识库目录/数据集管理行为稳定并补齐验证。`

## Goal

Decompose the current knowledge-management backend manager and frontend knowledge-bases page/hook
into smaller, reviewable units so that future directory-tree, dataset binding, and permission-scope
changes stop accumulating inside two oversized files, while preserving the current route and UI
behavior.

## Scope

- `backend/services/knowledge_management/manager.py`
- new bounded backend helper modules under `backend/services/knowledge_management/`
- `backend/app/modules/knowledge/routes/directory.py` only if wiring cleanup is needed
- `fronted/src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.js`
- `fronted/src/pages/KnowledgeBases.js`
- new bounded frontend helper hooks/components under `fronted/src/features/knowledge/knowledgeBases/`
- focused backend and frontend knowledge-management tests
- `docs/exec-plans/active/knowledge-management-refactor-phase-1.md`

## Non-Goals

- changing knowledge-management API paths or response envelopes
- changing upload approval flows or document preview flows
- redesigning the knowledge-bases page
- changing route-navigation or permission-model behavior
- broad cleanup of unrelated knowledge upload modules

## Preconditions

- Existing backend knowledge-management tests can run.
- Existing frontend knowledge-bases page and hook tests can run.
- `KnowledgeManagementManager` remains the stable backend entry point used by knowledge directory routes.
- `KnowledgeBases` remains the stable frontend page entry used by routing.

If any item is missing, stop and record it in `task-state.json.blocking_prereqs`.

## Impacted Areas

- backend knowledge-management scope calculation, directory guards, dataset create/update/delete,
  and permission-group scope validation
- knowledge directory route behavior exercised through `test_knowledge_directory_route_permissions_unit.py`
- frontend knowledge-bases page shell, directory tree, dataset table, breadcrumb navigation,
  dataset detail form, and create-dialog flow
- focused tests:
  - `backend/tests/test_knowledge_management_manager_unit.py`
  - `backend/tests/test_knowledge_directory_route_permissions_unit.py`
  - `fronted/src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.test.js`
  - `fronted/src/pages/KnowledgeBases.test.js`

## Phase Plan

Use stable phase ids. Do not renumber ids after execution has started.

### P1: Decompose backend knowledge-management orchestration

- Objective: Split scope resolution and dataset/directory mutation responsibilities out of the
  current backend manager while keeping `KnowledgeManagementManager` as the stable facade.
- Owned paths:
  - `backend/services/knowledge_management/manager.py`
  - new helper modules under `backend/services/knowledge_management/`
  - `backend/app/modules/knowledge/routes/directory.py` only if wiring cleanup is required
- Dependencies:
  - existing `KnowledgeTreeManager`
  - existing `KnowledgeDirectoryStore`
  - existing knowledge directory route contract
- Deliverables:
  - slimmer backend manager facade
  - extracted helper modules for scope calculation and mutation orchestration
  - unchanged backend knowledge admin behavior

### P2: Decompose frontend knowledge-bases page and hook

- Objective: Split the knowledge-bases page shell and page hook into smaller units for
  tree/navigation state, dataset actions, and page rendering without changing current behavior.
- Owned paths:
  - `fronted/src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.js`
  - `fronted/src/pages/KnowledgeBases.js`
  - new helper modules/components under `fronted/src/features/knowledge/knowledgeBases/`
- Dependencies:
  - existing `knowledgeApi`
  - existing `DirectoryTreeView` and create-dialog components
  - current page tests and route usage
- Deliverables:
  - slimmer page hook
  - extracted knowledge-bases state/action hooks
  - extracted page sections that preserve current test ids and interactions

### P3: Focused regression validation and task evidence

- Objective: Prove the bounded knowledge-management refactor preserved both backend and frontend
  behavior.
- Owned paths:
  - `backend/tests/test_knowledge_management_manager_unit.py`
  - `backend/tests/test_knowledge_directory_route_permissions_unit.py`
  - `fronted/src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.test.js`
  - `fronted/src/pages/KnowledgeBases.test.js`
  - task artifacts for this tranche
- Dependencies:
  - P1 and P2 completed
- Deliverables:
  - focused backend/frontend regression coverage
  - execution/test evidence for each acceptance criterion

## Phase Acceptance Criteria

### P1

- P1-AC1: `KnowledgeManagementManager` no longer directly owns all management-scope resolution,
  dataset guard checks, dataset mutation orchestration, and permission-group scope validation in
  one file.
- P1-AC2: existing knowledge directory route behavior and permission-scope semantics remain unchanged.
- P1-AC3: knowledge-management flows still fail fast on missing root nodes, out-of-scope nodes or
  datasets, and invalid dataset creation input.
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`

### P2

- P2-AC1: `useKnowledgeBasesPage.js` no longer directly owns all tree loading, breadcrumb
  navigation, dataset detail loading, drag-and-drop moves, and create-dialog orchestration in one
  file.
- P2-AC2: `KnowledgeBases.js` no longer mixes page shell, toolbar, table, detail form, and tree
  panel rendering in one file.
- P2-AC3: current page interactions, test ids, create/update/delete behavior, and dataset move
  behavior remain stable after extraction.
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T2`

### P3

- P3-AC1: focused backend and frontend knowledge-management tests pass against the final code
  state.
- P3-AC2: task artifacts record the exact commands run, verified acceptance coverage, and bounded
  residual risk.
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`

## Done Definition

- P1, P2, and P3 are completed.
- All acceptance ids have evidence in `execution-log.md` or `test-report.md`.
- `test_status` is `passed`.
- The knowledge-management backend facade, admin route contract, and frontend knowledge-bases page
  behavior remain stable.

## Blocking Conditions

- focused backend or frontend validation cannot run
- refactor would require changing public API paths or response envelopes
- preserving current behavior would require fallback branches or silent downgrade
- helper extraction would break permission-scope semantics, dataset create/update/delete behavior,
  or knowledge-bases page test contracts
