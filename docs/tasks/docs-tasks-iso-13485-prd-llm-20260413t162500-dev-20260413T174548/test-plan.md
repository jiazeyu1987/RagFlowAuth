# WS02 Implementation Test Plan

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T174548`
- Created: `2026-04-13T17:45:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS02-quality-system-hub-and-auth.md 开发 WS02：新增体系文件根入口、子路由前缀预留、工作台壳层与质量域 capability 扩展`

## Test Scope

必须验证以下内容：

- 前端路由表新增 `质量体系` 根路由和固定子路由前缀。
- 左侧导航只显示一个 `体系文件` 根入口，且进入 `/quality-system/*` 时保持高亮。
- `sub_admin` 可通过 capability 进入 `质量体系` 壳层，不要求全局管理员。
- `QualitySystem` 页面只提供壳层能力，不直接落入子域业务实现。
- 后端 auth payload 返回的 capability snapshot 含有质量域资源名，并满足 `quality_system.view/manage` 的最小权限边界。

以下内容明确不在本次测试范围：

- 文控、培训、变更、设备、批记录、投诉等子域真实业务表单。
- 审计导出、通知 payload 结构、数据库 schema 扩展。
- 其他工作流未来在 `/quality-system/*` 子路由下的真实业务实现。

## Environment

- Frontend working directory: `D:\ProjectPackage\RagflowAuth\fronted`
- Backend working directory: `D:\ProjectPackage\RagflowAuth`
- Node modules already present in `fronted/node_modules`
- Python test environment available from repo root with `pytest`
- Real browser validation uses Playwright against the local frontend session

## Accounts and Fixtures

- Frontend unit tests mock `useAuth` and inbox API responses.
- Backend unit tests use `PermissionSnapshot` fixtures and fake dependency objects.
- Real-browser validation requires:
  - a running frontend session serving the updated app
  - an authenticated `admin` or `sub_admin` session that can reach the shell route

如果缺少可登录账号或本地运行会话，测试必须失败并记录缺失前提，不能用截图造假或跳过说明替代。

## Commands

1. `npm test -- --runInBand --watchAll=false src/routes/routeRegistry.test.js src/components/Layout.test.js src/pages/QualitySystem.test.js`
   - Expected success signal: Jest exits with code 0 and the new quality-system route/shell assertions pass.
2. `pytest backend/tests/test_auth_me_service_unit.py -q`
   - Expected success signal: pytest exits with code 0 and auth payload capability snapshot assertions pass.
3. Real-browser validation with Playwright against the running app
   - Expected success signal: browser can open `/quality-system` and at least one reserved child route, confirm shell content and root-nav active state, and capture evidence artifacts.

## Test Cases

### T1: Route registry exposes quality-system root and reserved child routes

- Covers: P1-AC1
- Level: unit
- Command: `npm test -- --runInBand --watchAll=false src/routes/routeRegistry.test.js`
- Expected: root route exists in nav metadata; reserved child routes exist in `APP_ROUTES`; nav-only separation remains intact.

### T2: Sidebar visibility and active behavior support quality-system shell

- Covers: P1-AC1, P1-AC2
- Level: unit
- Command: `npm test -- --runInBand --watchAll=false src/components/Layout.test.js`
- Expected: `admin` and `sub_admin` can see the root nav item, viewer cannot; visiting `/quality-system/training` still highlights the `质量体系` root nav entry.

### T3: QualitySystem shell renders module cards, reserved child context, and work-queue panel

- Covers: P1-AC3
- Level: unit
- Command: `npm test -- --runInBand --watchAll=false src/pages/QualitySystem.test.js`
- Expected: root shell shows the module registry and work-queue panel; reserved child routes render selected-module context without leaking into child business flows.

### T4: Auth payload includes quality capability snapshot

- Covers: P1-AC2, P1-AC4
- Level: unit
- Command: `pytest backend/tests/test_auth_me_service_unit.py -q`
- Expected: payload contains the WS02 quality resource catalog; `sub_admin` gets `quality_system.view`; `admin` gets `quality_system.manage`.

### T5: Real browser can open quality-system shell and reserved child route

- Covers: P1-AC1, P1-AC3, P1-AC4
- Level: e2e
- Command: Playwright-driven manual verification against the running local app
- Expected: browser confirms the new nav entry, `/quality-system` shell, one reserved child route such as `/quality-system/training`, and captures concrete evidence files.

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Route registry | Root and reserved child routes are registered | unit | P1-AC1 | Jest output, `execution-log.md#Phase-P1` |
| T2 | Sidebar and guards | Root nav visibility and child-route active state are correct | unit | P1-AC1, P1-AC2 | Jest output, `execution-log.md#Phase-P1` |
| T3 | QualitySystem shell | Shell page renders cards, context, and work-queue panel without child business logic | unit | P1-AC3 | Jest output, `execution-log.md#Phase-P1` |
| T4 | Auth payload | Quality capability snapshot exists and grants shell access boundary correctly | unit | P1-AC2, P1-AC4 | pytest output, `execution-log.md#Phase-P1` |
| T5 | Browser validation | Real browser reaches root shell and reserved child route | e2e | P1-AC1, P1-AC3, P1-AC4 | `test-report.md`, Playwright evidence files |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright, npm, pytest
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. Because UI routing and navigation are in scope, use a real browser session and record screenshot or trace evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - all automated commands exit successfully
  - real-browser validation reaches both the root shell and at least one reserved child route
  - evidence demonstrates the nav entry, capability gate, and shell-only behavior
- Fail when:
  - any quality-system route is missing or unreachable
  - `sub_admin` still depends on admin-only routing to enter the shell
  - auth payload omits the quality capability snapshot
  - the shell page directly implements child business workflows instead of remaining a hub/placeholder
  - required browser evidence is missing

## Regression Scope

- Existing navigation entries in `routeRegistry.js`
- Sidebar active-route behavior for `/tools/*` and other existing sections
- `PermissionGuard` compatibility with route guard metadata
- Existing auth payload structure consumed by `useAuth`

## Reporting Notes

Write automated and browser results to `test-report.md`.

For the browser case, include evidence file paths for at least one screenshot or comparable artifact. If independent tester execution is not available in this thread, record that limitation explicitly instead of marking the tester stage complete without evidence.
