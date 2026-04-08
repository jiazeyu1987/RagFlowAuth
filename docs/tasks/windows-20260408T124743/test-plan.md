# Test Plan

- Task ID: `windows-20260408T124743`
- Created: `2026-04-08T12:47:43`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `将正式备份链路改为只做服务器本机备份，不再检查、不再执行也不再提示 Windows 副本状态；清理对应测试与状态文案。`

## Test Scope

验证以下内容：
- 后端正式备份任务不再依赖 Windows 副本状态。
- 数据安全设置响应和页面不再展示 Windows 正式备份信息。
- 恢复演练仍然只从本机备份任务中选择可恢复项。

不覆盖：
- 独立服务器备份拉取 GUI 的工作流。
- 真实 Windows 挂载或 CIFS 链路。

## Environment

- Windows 工作站仓库：`D:\ProjectPackage\RagflowAuth`
- Python 单元测试环境
- 前端单元测试环境
- 如执行 E2E，用仓库现有 Playwright 配置

## Accounts and Fixtures

- 后端测试使用临时 SQLite 和本地临时目录。
- 前端测试使用 mocked API payload。
- E2E 使用 mocked network route。

If any required item is missing, the tester must fail fast and record the missing prerequisite.

## Commands

- `python -m unittest backend.tests.test_backup_restore_audit_unit backend.tests.test_data_security_router_unit`
  - 预期信号：后端备份与设置响应测试通过。
- `npm test -- --runTestsByPath fronted/src/features/dataSecurity/api.test.js fronted/src/features/dataSecurity/useDataSecurityPage.test.js fronted/src/pages/DataSecurity.test.js --watch=false`
  - 预期信号：前端数据安全页相关单测通过。
- 如前端 E2E 可运行：`npx playwright test fronted/e2e/tests/admin.data-security.backup.failure.spec.js fronted/e2e/tests/admin.data-security.backup.polling.spec.js`
  - 预期信号：页面回归通过，断言不再依赖 Windows 正式备份状态。

## Test Cases

### T1: 后端正式备份仅由本机结果决定

- Covers: P1-AC1, P1-AC2
- Level: unit
- Command: `python -m unittest backend.tests.test_backup_restore_audit_unit`
- Expected: 本机成功时任务完成，本机失败时任务失败；不再聚合 Windows 副本状态消息。

### T2: 设置响应不再驱动 Windows 正式统计

- Covers: P1-AC3
- Level: unit
- Command: `python -m unittest backend.tests.test_data_security_router_unit`
- Expected: 设置响应仍包含本机备份统计，且不要求 Windows 正式统计作为页面前置。

### T3: 前端页面只展示本机正式备份

- Covers: P2-AC1
- Level: unit
- Command: `npm test -- --runTestsByPath fronted/src/pages/DataSecurity.test.js --watch=false`
- Expected: 页面仅展示本机备份路径、任务和高级设置，不再出现 Windows 备份卡片或状态文本。

### T4: Hook 与 API 不再依赖 Windows 正式字段

- Covers: P2-AC1, P2-AC2
- Level: unit
- Command: `npm test -- --runTestsByPath fronted/src/features/dataSecurity/api.test.js fronted/src/features/dataSecurity/useDataSecurityPage.test.js --watch=false`
- Expected: hook 与 API 规范化逻辑以本机备份为主，不再要求 Windows 备份字段。

### T5: 页面回归不再断言 Windows 状态

- Covers: P2-AC2
- Level: e2e
- Command: `npx playwright test fronted/e2e/tests/admin.data-security.backup.failure.spec.js fronted/e2e/tests/admin.data-security.backup.polling.spec.js`
- Expected: 备份完成回归只断言本机备份流程和任务完成状态。

### T6: 文档说明同步

- Covers: P2-AC3
- Level: unit
- Command: `python -c "from pathlib import Path; text = Path(r'D:\\ProjectPackage\\RagflowAuth\\docs\\maintance\\backup.md').read_text(encoding='utf-8'); assert '正式逻辑只要求服务器本机备份' in text"`
- Expected: 文档明确说明正式逻辑只要求服务器本机备份。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | 后端备份服务 | 正式结果只取决于本机备份 | unit | P1-AC1, P1-AC2 | unittest 输出 |
| T2 | 设置响应 | 页面设置不再依赖 Windows 正式统计 | unit | P1-AC3 | unittest 输出 |
| T3 | 数据安全页 | 页面移除 Windows 正式备份展示 | unit | P2-AC1 | jest 输出 |
| T4 | 前端 hook/api | 前端不再要求 Windows 正式字段 | unit | P2-AC1, P2-AC2 | jest 输出 |
| T5 | 页面回归 | 备份完成流不再断言 Windows 状态 | e2e | P2-AC2 | playwright 输出 |
| T6 | 维护文档 | 文档说明正式逻辑改为本机单份 | unit | P2-AC3 | 命令输出 |

## Evaluator Independence

- Mode: full-context
- Validation surface: real-runtime
- Required tools: python, unittest, npm, playwright
- First-pass readable artifacts: prd.md, test-plan.md, execution-log.md, task-state.json
- Withheld artifacts:
- Real environment expectation: 在真实仓库环境中运行后端与前端测试，必要时运行真实前端测试命令；不以聊天描述替代测试证据。
- Escalation rule: If a planned validation command cannot run, stop and record the missing prerequisite instead of inferring success.

## Pass / Fail Criteria

- Pass when:
  - 后端测试通过并证明 Windows 副本不再参与正式结果。
  - 前端页面与 hook/api 测试通过且不再展示 Windows 正式备份信息。
  - 文档已同步更新。
- Fail when:
  - 任一正式链路仍出现 Windows 状态、错误或设置提示。
  - 备份完成逻辑仍依赖 replica 状态。
  - 前端测试或后端测试出现未收敛的 Windows 断言。

## Regression Scope

- `backend/services/data_security/backup_service.py`
- `backend/app/modules/data_security/support.py`
- `backend/services/data_security/settings_policy.py`
- `fronted/src/features/dataSecurity/`
- `fronted/src/pages/DataSecurity.js`

## Reporting Notes

Write results to `test-report.md`.
