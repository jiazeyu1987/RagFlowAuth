# Knowledge Management Refactor Test Plan

- Task ID: `tranche-knowledge-management-knowledgebases-h-20260408T053800`
- Created: `2026-04-08T05:33:43`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构：以下一 tranche 聚焦 knowledge management 模块，拆分后端 KnowledgeManagementManager 与前端 KnowledgeBases 页面和 hook，保持知识库目录/数据集管理行为稳定并补齐验证。`

## Test Scope

Validate that the bounded knowledge-management refactor preserves:

- backend management-scope resolution, directory guard checks, dataset mutations, and knowledge
  admin route behavior
- frontend knowledge-bases page loading, dataset detail editing, dataset creation, dataset delete
  request flow, and directory-tree interactions

Out of scope:

- upload approval or document preview flows
- route-navigation or permission-model regressions outside the knowledge-bases page
- visual redesign or accessibility restyling checks

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Backend: Python pytest / unittest-compatible environment already used by repo tests
- Frontend: Node.js/npm with Jest via `react-scripts test`

## Accounts and Fixtures

- backend tests rely on temporary SQLite fixtures plus mocked Ragflow datasets and knowledge-tree
  data
- frontend tests rely on mocked `useAuth` and mocked `knowledgeApi`
- if either Python or npm tooling is unavailable, fail fast and record the missing prerequisite

## Commands

- `python -m pytest backend/tests/test_knowledge_management_manager_unit.py backend/tests/test_knowledge_directory_route_permissions_unit.py`
  - Expected success signal: focused backend knowledge-management suites pass
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.test.js src/pages/KnowledgeBases.test.js`
  - Expected success signal: focused frontend knowledge-bases suites pass

## Test Cases

### T1: Backend knowledge-management contract regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2
- Level: unit / route integration
- Command: `python -m pytest backend/tests/test_knowledge_management_manager_unit.py backend/tests/test_knowledge_directory_route_permissions_unit.py`
- Expected: management-scope behavior, permission guards, dataset actions, and admin route
  contracts remain stable

### T2: Frontend knowledge-bases page regression

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/knowledgeBases/useKnowledgeBasesPage.test.js src/pages/KnowledgeBases.test.js`
- Expected: page shell, knowledge-base create/delete flow, selection, and tree/table interactions
  remain stable

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend knowledge management | manager decomposition preserves scope guards, dataset actions, and admin routes | unit/route integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1, P3-AC2 | `test-report.md#T1` |
| T2 | frontend knowledge bases | page/hook decomposition preserves page interactions and knowledge-base actions | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC1, P3-AC2 | `test-report.md#T2` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: python, pytest, npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. If a UI or interaction path is in scope, use a real browser or session and record concrete evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - T1 and T2 pass
  - backend manager semantics and frontend knowledge-bases interactions remain stable
- Fail when:
  - either focused test command fails
  - permission-scope semantics, dataset create/update/delete behavior, or page interactions regress

## Regression Scope

- `backend/services/knowledge_management/*`
- `backend/app/modules/knowledge/routes/directory.py`
- `backend/tests/test_knowledge_management_manager_unit.py`
- `backend/tests/test_knowledge_directory_route_permissions_unit.py`
- `fronted/src/features/knowledge/knowledgeBases/*`
- `fronted/src/pages/KnowledgeBases.js`
- `fronted/src/pages/KnowledgeBases.test.js`

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact commands and whether each suite passed.
