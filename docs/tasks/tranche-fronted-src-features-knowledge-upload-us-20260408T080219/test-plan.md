# Knowledge Upload Hook Refactor Test Plan

- Task ID: `tranche-fronted-src-features-knowledge-upload-us-20260408T080219`
- Created: `2026-04-08T08:02:19`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `缁х画杩涜鍓嶅悗绔噸鏋勭洿鍒伴噸鏋勭粨鏉燂細鏈?tranche 鑱氱劍 fronted/src/features/knowledge/upload/useKnowledgeUploadPage.js锛屾媶鍒嗙煡璇嗗簱鍔犺浇绛涢€夈€佹墿灞曞悕閰嶇疆绠＄悊銆佹枃浠堕€夋嫨涓庝笂浼犳祦绋嬬姸鎬侊紝淇濇寔 KnowledgeUpload 椤甸潰杩斿洖濂戠害涓庣幇鏈?Jest 娴嬭瘯琛屼负绋冲畾`

## Test Scope

Validate that the bounded frontend refactor preserves:

- visible knowledge-base filtering and dataset selection behavior
- file selection and upload submission flow
- allowed-extension loading failure and fail-fast upload blocking
- `KnowledgeUpload` page consumption of the shared hook contract
- upload feature API payload normalization

Out of scope:

- real-browser upload interaction
- backend approval processing after submit
- unrelated knowledge feature pages and NAS browsing flows

## Environment

- Platform: Windows PowerShell in `D:\ProjectPackage\RagflowAuth\fronted`
- Frontend: CRA/Jest via `npm test`
- Test runtime: mocked APIs, auth hook, and page child components already embedded in the focused
  Jest suites

## Accounts and Fixtures

- tests rely on mocked `useAuth`, `knowledgeApi`, and `knowledgeUploadApi`
- no live backend, browser automation, or database fixture is required
- if `npm` or Jest is unavailable, fail fast and record the missing prerequisite

## Commands

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/upload/useKnowledgeUploadPage.test.js src/pages/KnowledgeUpload.test.js src/features/knowledge/upload/api.test.js`
  - Expected success signal: focused knowledge-upload suites pass in a single non-watch Jest run

## Test Cases

### T1: Knowledge upload hook, page, and API regression

- Covers: P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2
- Level: unit/component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/knowledge/upload/useKnowledgeUploadPage.test.js src/pages/KnowledgeUpload.test.js src/features/knowledge/upload/api.test.js`
- Expected: helper extraction preserves upload hook state flow, page wiring, and upload API payload
  normalization without changing current fail-fast behavior

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | frontend knowledge upload | shared hook decomposition preserves hook state flow, page contract, and upload API normalization | unit/component | P1-AC1, P1-AC2, P1-AC3, P2-AC1, P2-AC2 | `test-report.md#T1` |

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
  - hook/page/API behavior stays stable under the existing tests
- Fail when:
  - the command fails
  - helper extraction breaks the hook return contract or current fail-fast error behavior

## Regression Scope

- `fronted/src/features/knowledge/upload/useKnowledgeUploadPage.js`
- new helper module(s) under `fronted/src/features/knowledge/upload/`
- `fronted/src/pages/KnowledgeUpload.js`
- focused tests listed above

## Reporting Notes

- Write results to `test-report.md`.
- Record the exact command and whether it passed.
