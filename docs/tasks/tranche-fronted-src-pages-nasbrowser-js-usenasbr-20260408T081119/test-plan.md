# Nas Browser Page Refactor Test Plan

- Task ID: `tranche-fronted-src-pages-nasbrowser-js-usenasbr-20260408T081119`
- Created: `2026-04-08T08:11:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/pages/NasBrowser.js锛屾媶鍒嗛〉闈㈠ご閮ㄥ鑸€佽矾寰勯潰鍖呭眿銆佸鍏ヨ繘搴﹂潰鏉裤€佹枃浠跺垪琛ㄨ〃鏍煎拰瀵煎叆瀵硅瘽妗嗙瓑娓叉煋鍖哄潡锛屼繚鎸?useNasBrowserPage 濂戠害銆佽矾鐢辫涓轰笌鐜版湁 Jest 娴嬭瘯绋冲畾`

## Test Scope

Validate that the bounded frontend refactor preserves:

- `useNasBrowserPage` hook state initialization and import actions
- `NasBrowser` page rendering and file-import interaction
- the page-facing hook contract consumed by the route page

Out of scope:

- real-browser NAS browsing
- live NAS API integration
- unrelated knowledge feature pages

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend: CRA/Jest via `npm test`
- Test runtime: mocked NAS API, knowledge API, and auth hook embedded in the focused Jest suites

## Accounts and Fixtures

- tests rely on mocked `useAuth`, `knowledgeApi`, and `nasApi`
- no live NAS server, backend, or browser automation is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/nasBrowser/useNasBrowserPage.test.js src/pages/NasBrowser.test.js`
  - Expected success signal: focused NAS browser hook and page suites pass in a single non-watch
    Jest run

## Test Cases

### T1: NAS browser hook and page regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/nasBrowser/useNasBrowserPage.test.js src/pages/NasBrowser.test.js`
- Expected: page component extraction preserves the hook state flow, NAS item rendering, and file
  import action wiring without changing current route-page behavior

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend NAS browser | page decomposition preserves hook/page wiring and import interactions | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: npm, react-scripts test
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: run the focused Jest command against the real repo state in
  `fronted/`
- Escalation rule: do not inspect withheld artifacts until the tester has produced an initial
  verdict

## Pass / Fail Criteria

- Pass when:
  - the focused Jest command succeeds
  - hook/page behavior stays stable under the existing tests
- Fail when:
  - the command fails
  - page extraction breaks the `useNasBrowserPage` integration or import interaction behavior

## Regression Scope

- `fronted/src/pages/NasBrowser.js`
- new component module(s) under `fronted/src/features/knowledge/nasBrowser/`
- `fronted/src/features/knowledge/nasBrowser/useNasBrowserPage.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
