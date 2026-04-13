# Test Plan

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173900`
- Created: `2026-04-13T17:39:00`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS07-audit-and-evidence-export.md 开发 WS07：补齐统一审计事件、证据导出、全局搜索与智能对话留痕，并完成后端/前端/测试交付`

## Test Scope

- 验证后端统一审计结构、搜索留痕、对话留痕和证据导出是否满足 PRD。
- 验证前端审计页是否能检索和导出 WS07 新事件，并稳定展示新增上下文。
- 验证范围不包含新增导航、能力资源名调整、其他业务域的埋点扩展。

## Environment

- Workspace: `D:\ProjectPackage\RagflowAuth`
- Backend tests:
  - Python 3.12+
  - 可直接运行仓库根目录 `pytest`
- Frontend tests:
  - `fronted/` 下 `npm` 依赖已安装
  - 可运行 `react-scripts test`
- Browser validation:
  - 本地前后端能启动
  - 浏览器可登录管理员账号
  - 至少一个知识库、一个聊天助手可用
  - 若以上任一条件缺失，tester 必须 fail fast 并在 `test-report.md` 记录缺失项

## Accounts and Fixtures

- 管理员账号，用于访问 `/api/audit/events`、导出证据包、执行搜索和聊天。
- 至少一个对管理员可见的知识库数据集。
- 至少一个可发起问答的聊天助手。
- 后端单测使用临时 sqlite 测试库，不依赖真实线上数据。

## Commands

- `python -m pytest backend/tests/test_audit_events_api_unit.py backend/tests/test_audit_evidence_export_api_unit.py backend/tests/test_audit_log_manager_unit.py [新增 WS07 后端测试文件]`
  - 预期：所有后端 WS07 定向单测通过。
- `npm test -- --runInBand --watch=false src/features/audit/api.test.js src/features/audit/useAuditLogsPage.test.js src/pages/AuditLogs.test.js [新增 WS07 前端测试文件]`
  - 预期：所有前端 WS07 定向测试通过。
- 真实浏览器验证命令按实际环境选择：
  - 优先：在 `fronted/` 下使用 Playwright 或现有浏览器工具打开系统并完成搜索、聊天、审计检索、证据导出。
  - 预期：形成至少一个真实浏览器证据文件，如 screenshot、trace、video 或 HAR。

## Test Cases

### T1: 后端审计查询契约

- Covers: P1-AC1
- Level: unit
- Command: `python -m pytest backend/tests/test_audit_events_api_unit.py`
- Expected: `/api/audit/events` 返回稳定 envelope，新增字段不破坏既有查询与返回结构。

### T2: 搜索与对话留痕后端路径

- Covers: P1-AC2, P1-AC3, P1-AC5
- Level: unit
- Command: `python -m pytest [新增 WS07 search/chat 审计测试文件]`
- Expected: 搜索成功时写入 `global_search` 事件；对话完成时写入 `smart_chat` 事件；缺失必要前提时显式失败。

### T3: 证据导出携带 WS07 事件

- Covers: P1-AC4, P1-AC5
- Level: unit
- Command: `python -m pytest backend/tests/test_audit_evidence_export_api_unit.py [新增证据导出补充测试文件]`
- Expected: 导出包包含搜索/对话相关事件及 manifest/checksum，一致性校验通过。

### T4: 前端审计页状态与导出交互

- Covers: P2-AC1, P2-AC3
- Level: unit
- Command: `npm test -- --runInBand --watch=false src/features/audit/api.test.js src/features/audit/useAuditLogsPage.test.js src/pages/AuditLogs.test.js`
- Expected: 新增查询参数和导出动作经由 feature api/hook/page 稳定工作，既有分页与列表行为保持正常。

### T5: 前端对搜索/对话类事件展示

- Covers: P2-AC2, P2-AC3
- Level: unit
- Command: `npm test -- --runInBand --watch=false [新增 WS07 前端展示测试文件]`
- Expected: 审计页对 `global_search`、`smart_chat` 或相关文档调用类事件展示可读摘要。

### T6: 真实浏览器管理员验收

- Covers: P1-AC2, P1-AC3, P1-AC4, P2-AC1, P2-AC2
- Level: manual
- Command: 使用 Playwright 或真实浏览器完成一次搜索、一次对话、一次审计检索和一次证据导出。
- Expected: 审计页可看到新生成的事件，导出成功，测试报告附带真实浏览器证据文件路径。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | audit api | 审计查询契约稳定 | unit | P1-AC1 | `test-report.md` + pytest output |
| T2 | search/chat backend | 搜索与对话写入统一质量审计事件 | unit | P1-AC2, P1-AC3, P1-AC5 | `test-report.md` + pytest output |
| T3 | evidence export | 导出包携带 WS07 事件且摘要可校验 | unit | P1-AC4, P1-AC5 | `test-report.md` + pytest output |
| T4 | audit frontend | 查询与导出交互稳定 | unit | P2-AC1, P2-AC3 | `test-report.md` + Jest output |
| T5 | audit frontend | 搜索/对话事件展示可读 | unit | P2-AC2, P2-AC3 | `test-report.md` + Jest output |
| T6 | integrated UI | 管理员在真实浏览器完成搜索、对话、审计检索、导出 | manual | P1-AC2, P1-AC3, P1-AC4, P2-AC1, P2-AC2 | `test-report.md` + browser evidence files |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: pytest, npm/react-scripts, playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and runtime. Because UI interactions are in scope, final validation must use a real browser session and attach concrete evidence.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when:
  - 所有定向后端测试通过。
  - 所有定向前端测试通过。
  - 浏览器验证确认能生成并检索 WS07 事件且能触发导出。
  - 每个 acceptance id 都在至少一个测试用例中得到通过证据。
- Fail when:
  - 搜索或对话没有产生审计事件。
  - 导出包缺少 WS07 相关事件或 manifest/checksum 不一致。
  - 审计页无法检索或导出新增事件。
  - 真实浏览器验证缺少管理员账号/知识库/聊天助手或缺少证据文件。

## Regression Scope

- 既有 `/api/audit/events` 查询兼容性。
- 既有 `AuditLogs` 页面分页和筛选行为。
- 搜索返回结果本身不应因新增留痕而改变接口契约。
- 对话流式响应和 citation sources 持久化不应因新增审计写入而损坏。
- 现有证据导出中的电子签名、审批、通知、备份、恢复演练内容仍应保留。

## Reporting Notes

将每个测试命令的结果、浏览器验证步骤、证据文件路径和最终 verdict 写入 `test-report.md`。

The tester must remain independent from the executor and should prefer blind-first-pass unless the task explicitly needs full-context evaluation.
