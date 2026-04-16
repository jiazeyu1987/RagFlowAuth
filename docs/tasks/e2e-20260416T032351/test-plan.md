# Test Plan

- Task ID: `e2e-20260416T032351`
- Created: `2026-04-16T03:23:51`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `为当前审批矩阵编写 E2E 测试用例，尽量覆盖完整的文控矩阵主流程、关键错误场景和审计展示`

## Test Scope

验证当前审批矩阵在文控页面和日志审计页面中的浏览器行为，重点覆盖：

- 文控页面的矩阵预览主流程
- 文件小类必填校验
- 注册条件不命中时不展示注册会签
- 矩阵解析失败时的前端错误展示
- 提交审批后当前步骤语义、岗位和审批人展示
- 审计页中矩阵流转 action/source/上下文摘要/筛选

不在本轮范围：真实后端数据库联调、实际审批人点击 approve/reject 的跨页面长链路。

## Environment

- Windows 本地开发环境
- `fronted/playwright.config.js` 自动拉起前后端测试服务
- 独立测试库：`E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\auth-document-matrix.db`
- 使用 `adminTest + mockAuthMe` 进行 mocked 浏览器 E2E

## Accounts and Fixtures

- `adminTest` 存储态账号
- `mockAuthMe` 覆盖的管理员能力：`quality_system.view/manage`、`document_control.*`、`audit_events.view`
- mocked fixtures：
  - 文控 document detail
  - matrix preview 响应
  - submit approval 响应
  - operation approval detail 响应
  - audit events 响应
  - quality system config file categories 响应

如果 Playwright 无法使用隔离测试库，测试必须失败并记录该前提缺失。

## Commands

- `npx playwright test e2e/tests/document-control.matrix.spec.js e2e/tests/document-control.matrix.validation.spec.js e2e/tests/document-control.matrix.preview-errors.spec.js e2e/tests/audit.logs.document-control-matrix.spec.js --workers=1`
  - 期望：全部通过，且可在独立 `E2E_TEST_DB_PATH` 下运行

## Test Cases

### T1: 文控矩阵预览主流程

- Covers: P1-AC1, P2-AC1
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.spec.js --workers=1`
- Expected: 页面显示编制/会签/批准岗位与展开审批人，提交后显示当前步骤语义、岗位和待审批人

### T2: 现有覆盖缺口已被补齐并可执行

- Covers: P1-AC2
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.validation.spec.js e2e/tests/document-control.matrix.preview-errors.spec.js --workers=1`
- Expected: 缺口分析中的文件小类校验、注册条件分支、矩阵错误态都已有浏览器断言并可运行

### T3: 文件小类必填校验

- Covers: P2-AC2
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.validation.spec.js --workers=1`
- Expected: 未选择文件小类时，浏览器中阻止提交并展示明确错误

### T4: 注册条件不命中

- Covers: P2-AC3
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.validation.spec.js --workers=1`
- Expected: `registration_ref` 为空时，矩阵预览中不出现“注册”会签岗位，且其他会签保持正常

### T5: 矩阵解析错误展示

- Covers: P2-AC2
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.preview-errors.spec.js --workers=1`
- Expected: 编制岗位不匹配、岗位无人等错误会在矩阵预览区域清晰显示

### T6: 审计页展示矩阵流转

- Covers: P3-AC1
- Level: e2e
- Command: `npx playwright test e2e/tests/audit.logs.document-control-matrix.spec.js --workers=1`
- Expected: 审计页展示 `document_control_transition` 的中文标签、来源、文件小类、当前步骤、模式，并可按 source/action 过滤

### T7: 隔离测试库下的整组命令通过

- Covers: P3-AC2
- Level: e2e
- Command: `npx playwright test e2e/tests/document-control.matrix.spec.js e2e/tests/document-control.matrix.validation.spec.js e2e/tests/document-control.matrix.preview-errors.spec.js e2e/tests/audit.logs.document-control-matrix.spec.js --workers=1`
- Expected: 在 `E2E_TEST_DB_PATH` 指向独立数据库时整组命令通过

### T8: 测试报告记录环境与剩余风险

- Covers: P3-AC3
- Level: manual-review
- Command: `n/a`
- Expected: `test-report.md` 记录环境、执行命令、通过情况和未覆盖风险

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 文控审批矩阵 | 主流程预览与提交后步骤展示 | e2e | P1-AC1, P2-AC1 | test-report.md |
| T2 | 覆盖审查 | 缺口项已落实为浏览器断言 | e2e | P1-AC2 | test-report.md |
| T3 | 文控审批矩阵 | 文件小类必填校验 | e2e | P2-AC2 | test-report.md |
| T4 | 文控审批矩阵 | 注册条件不命中 | e2e | P2-AC3 | test-report.md |
| T5 | 文控审批矩阵 | 关键矩阵错误展示 | e2e | P2-AC2 | test-report.md |
| T6 | 日志审计 | 矩阵流转可读与可筛选 | e2e | P3-AC1 | test-report.md |
| T7 | 执行环境 | 隔离测试库下整组命令通过 | e2e | P3-AC2 | test-report.md |
| T8 | 测试报告 | 环境与剩余风险记录完整 | manual-review | P3-AC3 | test-report.md |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实浏览器中运行前端页面，接口采用测试内 mock，环境由 Playwright 配置拉起
- Escalation rule: 若默认测试库被占用，必须切换到独立 `E2E_TEST_DB_PATH`，不得回退到共享测试库

## Pass / Fail Criteria

- Pass when:
  - 目标 E2E spec 全部通过
  - 主流程、错误态、审计展示三类场景均有浏览器断言
- Fail when:
  - 任一关键矩阵场景没有浏览器级断言
  - Playwright 只能依赖共享测试库且无法在隔离库下运行

## Regression Scope

- 文控页面现有 mocked 矩阵 E2E
- 审计页现有 quality system config E2E
- 文控前端单测与后端矩阵相关单测作为旁证，不替代本轮 E2E

## Reporting Notes

- 执行结果写入 test-report.md
- 如有失败，明确区分为代码问题、契约问题、或环境占用问题
