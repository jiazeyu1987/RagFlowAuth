# Download Controller Refactor Test Plan

- Task ID: `tranche-fronted-src-features-download-usedownloa-20260408T074226`
- Created: `2026-04-08T07:42:26`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续进行前后端重构直到重构结束：本 tranche 聚焦 fronted/src/features/download/useDownloadPageController.js，拆分配置持久化、当前下载会话动作、历史面板动作，保持 paper/patent 下载页行为与测试契约稳定`

## Test Scope

Validate that the bounded frontend refactor preserves:

- shared controller stop flow, history coordination, local configuration loading, and action wiring
- paper/patent page wrapper hooks that compose the shared controller
- paper/patent page components that consume the wrapper hook contract

Out of scope:

- live browser validation against a running backend
- backend API behavior or download worker execution
- redesign or styling validation beyond existing component-test coverage

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth`
- Frontend: Node.js/npm with Jest via `react-scripts test`
- Test runtime: mocked controller dependencies, mocked `useAuth`, and mocked page components where
  already used by the existing suites

## Accounts and Fixtures

- controller tests rely on mocked `manager`, mocked `useDownloadHistory`, and mocked
  `useDownloadSessionPolling`
- page-wrapper tests rely on mocked `useAuth`, mocked `useNavigate`, and mocked controller return
  values
- page component tests rely on mocked wrapper hooks and mocked child components
- if npm or `react-scripts test` is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/download/useDownloadPageController.test.js src/features/paperDownload/usePaperDownloadPage.test.js src/features/patentDownload/usePatentDownloadPage.test.js src/pages/PaperDownload.test.js src/pages/PatentDownload.test.js`
  - Expected success signal: focused frontend suites pass

## Test Cases

### T1: Shared download controller and wrapper regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/download/useDownloadPageController.test.js src/features/paperDownload/usePaperDownloadPage.test.js src/features/patentDownload/usePatentDownloadPage.test.js src/pages/PaperDownload.test.js src/pages/PatentDownload.test.js`
- Expected: controller decomposition preserves the shared hook contract, wrapper behavior, and page
  rendering expectations

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend download controller | shared hook decomposition preserves controller contract and page-wrapper behavior | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused Jest suites against the real repo state
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - T1 passes
  - the shared controller contract and page-level expectations remain unchanged
- Fail when:
  - the focused Jest command fails
  - controller return fields, wrapper behavior, or page expectations regress

## Regression Scope

- `fronted/src/features/download/useDownloadPageController.js`
- new helper hooks/utilities under `fronted/src/features/download/`
- `fronted/src/features/paperDownload/usePaperDownloadPage.js`
- `fronted/src/features/patentDownload/usePatentDownloadPage.js`
- focused controller/wrapper/page tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether the focused Jest suite passed.
