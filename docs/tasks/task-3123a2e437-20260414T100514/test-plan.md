# 前端用户可见文案规范化 Test Plan

- Task ID: `task-3123a2e437-20260414T100514`
- Created: `2026-04-14T10:05:14`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `解决当前前端里的乱码问题、英文不是中文的问题、描述不正式的问题`

## Test Scope

- 验证当前前端真实可见的英文/不正式文案已统一为正式中文
- 验证范围必须覆盖 `/tools`、`/unauthorized`、`/quality-system`、`/quality-system/change-control`、`/quality-system/governance-closure`
- 验证范围必须覆盖全局 loading / error / empty copy 热点，包括 `App`、`PermissionGuard`、`UserManagement`、`KnowledgeUpload`、`OnlyOfficeViewer`
- 不验证后端业务正确性、数据库写入结果或全站无英文；内部日志、变量名、`data-testid` 和路由 path 不在本次断言范围内

## Environment

- 运行目录以 `fronted/` 为准
- 使用仓库内现有 `fronted/playwright.config.js` 启动 real-browser 验证，配置会自动拉起本地前端和后端测试服务
- 依赖现有 Playwright 浏览器安装与本地 Node/Python 环境
- 使用仓库内现成认证夹具和路由拦截，不新增产品侧 mock 数据

## Accounts and Fixtures

- `/tools`、`/quality-system`、`/quality-system/change-control`、`/quality-system/governance-closure` 使用现有 `admin` 认证夹具
- `/unauthorized` 使用现有 `viewer` 认证夹具
- `UserManagement` 与 `KnowledgeUpload` 使用已存在的授权用户夹具或 admin 夹具
- `OnlyOfficeViewer` 的错误分支用浏览器侧可控条件触发，确保验证的是真实页面行为而不是产品降级

## Commands

- `npm test -- --runInBand --watch=false --testPathPattern="(App|PermissionGuard|UserManagement|KnowledgeUpload|Tools|Unauthorized|QualitySystem|ChangeControl|userFacingErrorMessages|OnlyOfficeViewer)"` - Expected success signal: Jest 退出码为 0，相关文案断言全部通过。
- `npm run build` - Expected success signal: 前端构建成功，没有因文案替换引入的语法或打包错误。
- `npx playwright test e2e/tests/tools.navigation.spec.js e2e/tests/rbac.unauthorized.spec.js e2e/tests/routes.direct-pages.spec.js --project=chromium` - Expected success signal: real-browser 用例全部通过，且通过/失败都保留 trace / screenshot / video，并在测试报告里记录证据文件路径。

## Test Cases

### T1: Global shell and shared copy are Chinese

- Covers: P1-AC1, P1-AC2
- Level: e2e
- Command: `npm test -- --runInBand --watch=false --testPathPattern="(App|PermissionGuard|UserManagement|KnowledgeUpload|OnlyOfficeViewer)"`; `npx playwright test e2e/tests/routes.direct-pages.spec.js --project=chromium`
- Expected: `App`、`PermissionGuard`、`UserManagement`、`KnowledgeUpload` 与 `OnlyOfficeViewer` 的用户可见 loading/error/empty copy 为正式中文，real-browser 中可核验。

### T2: Tools page copy is formal Chinese

- Covers: P2-AC1, P2-AC2
- Level: e2e
- Command: `npm test -- --runInBand --watch=false --testPathPattern="Tools"`; `npx playwright test e2e/tests/tools.navigation.spec.js --project=chromium`
- Expected: `/tools` 页面标题、卡片描述、分页、空态与错误提示为正式中文，分页切换和工具跳转仍可用，浏览器证据文件可回溯。

### T3: Existing routed pages and shared error mapping are Chinese

- Covers: P3-AC1, P3-AC2
- Level: e2e
- Command: `npm test -- --runInBand --watch=false --testPathPattern="(Unauthorized|QualitySystem|ChangeControl|userFacingErrorMessages|GovernanceClosure)"`; `npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/routes.direct-pages.spec.js --project=chromium`
- Expected: `/unauthorized`、`/quality-system`、`/quality-system/change-control`、`/quality-system/governance-closure` 与共享错误映射均返回正式中文，real-browser 中有截图、trace 或视频证据。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | `App` / `PermissionGuard` / `UserManagement` / `KnowledgeUpload` / `OnlyOfficeViewer` | 全局加载、错误、空态与预览错误文案是否为正式中文 | unit + real-browser | P1-AC1, P1-AC2 | `test-report.md` + Playwright screenshot / trace / video |
| T2 | `/tools` | 页面标题、描述、分页、空态与工具卡片描述是否为正式中文 | unit + real-browser | P2-AC1, P2-AC2 | `test-report.md` + Playwright screenshot / trace / video |
| T3 | `/unauthorized`、`/quality-system`、WS04、WS08、共享错误映射 | 既有路由与错误码映射是否输出正式中文 | unit + real-browser | P3-AC1, P3-AC2 | `test-report.md` + Playwright screenshot / trace / video |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实仓库与真实本地运行环境中执行；如果是 UI 路径，必须使用真实浏览器并记录可核验证据
- Escalation rule: 在获得初次判定前，不要查看被 withheld 的工件，也不要让执行者改写测试结论

## Pass / Fail Criteria

- Pass when: 三个测试案例都通过，所有 acceptance id 都有对应证据，且浏览器证据文件可在报告中追溯
- Pass when: `/tools`、全局 loading/error/empty copy、既有业务页与共享错误映射都不再向用户展示英文自然语言
- Fail when: 任意目标路由仍显示英文自然语言，测试只能依赖产品侧 fallback/mock 才通过，或证据文件没有被明确引用

## Regression Scope

- `fronted/src/App.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/pages/Tools.js`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/pages/KnowledgeUpload.js`
- `fronted/src/shared/documents/preview/OnlyOfficeViewer.js`
- `fronted/src/pages/Unauthorized.js`
- `fronted/src/pages/ChangeControl.js`
- `fronted/src/pages/QualitySystem.js`
- `fronted/src/features/governanceClosure/GovernanceClosureWorkspace.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`
- `fronted/e2e/tests/tools.navigation.spec.js`
- `fronted/e2e/tests/rbac.unauthorized.spec.js`
- `fronted/e2e/tests/routes.direct-pages.spec.js`

## Reporting Notes

- 结果写入 `test-report.md`
- 每个 real-browser 通过项都要写清楚访问路由、认证角色、断言摘要和证据文件路径
- 不要把 `execution-log.md` 或 `task-state.json` 的内容泄漏到 blind-first-pass 的首轮结论里
