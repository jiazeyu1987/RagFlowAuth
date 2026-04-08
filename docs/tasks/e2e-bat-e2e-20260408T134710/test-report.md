# Test Report

- Task ID: `e2e-bat-e2e-20260408T134710`
- Created: `2026-04-08T13:47:10`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `文档E2E自动测试.bat 补充齐全登录部分需要的e2e测试`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-browser
- Tools: npx, Playwright, Python
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Record the tester's first-pass visibility honestly. In `blind-first-pass`, the tester should record `yes` only after writing an initial verdict before inspecting withheld artifacts.

## Results

Add one subsection per executed test case using the test case ids from `test-plan.md`.

Each subsection should use this shape:

`### T1: concise title`

- `Result: passed|failed|blocked|not_run`
- `Covers: P1-AC1`
- `Command run: exact command or manual action`
- `Environment proof: runtime, URL, browser session, fixture, or deployment proof`
- `Evidence refs: screenshot, video, trace, HAR, or log refs`
- `Notes: concise findings`

For `real-browser` validation, include at least one evidence ref that resolves to an existing non-task-artifact file, such as `evidence/home.png`, `evidence/trace.zip`, or `evidence/session.har`.

### T1: Doc UI login succeeds for bootstrap admin

- Result: passed
- Covers: P1-AC1
- Command run: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.login.spec.js --workers=1`
- Environment proof: Playwright (Chromium) run via docs config with local web servers
- Evidence refs: fronted/playwright-report/data/5f56b45dc198363d66831a341bd2681d5a231fa8.zip
- Notes: Spec passed and included success flow assertions.

### T2: Doc UI login failure shows error messaging

- Result: passed
- Covers: P1-AC2
- Command run: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.login.spec.js --workers=1`
- Environment proof: Playwright (Chromium) run via docs config with local web servers
- Evidence refs: fronted/playwright-report/data/5f56b45dc198363d66831a341bd2681d5a231fa8.zip
- Notes: Spec passed and included failure messaging assertions.

### T3: Doc batch runner includes login spec via manifest

- Result: failed
- Covers: P1-AC3
- Command run: `python scripts/run_doc_e2e.py --repo-root D:\ProjectPackage\RagflowAuth`
- Environment proof: Command execution from repo root; completed with exit code 1 after running multiple doc specs
- Evidence refs: `doc/test/reports/doc_e2e_report_latest.md`
- Notes: Doc report file exists and lists `e2e/tests/docs.login.spec.js` as PASS, but the batch runner exited non-zero due to other doc spec failures.

## Final Verdict

- Outcome: failed
- Verified acceptance ids: P1-AC1, P1-AC2
- Blocking prerequisites: None observed.
- Summary: Narrow login spec passed and doc report lists the login spec as PASS, but the doc batch runner exited with code 1, so P1-AC3 is not satisfied in this run.

## Open Issues

- T3 failed due to batch runner non-zero exit; doc runner must complete successfully to verify manifest wiring end-to-end.
