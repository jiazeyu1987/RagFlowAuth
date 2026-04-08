# Notification Refactor Test Plan

- Task ID: `notification-20260408T021230`
- Created: `2026-04-08T02:12:30`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续推进系统前后端重构，完成 notification 模块第一期局部重构，保持现有行为与接口契约稳定`

## Test Scope

验证 notification 第一批重构没有改变以下行为：

- 管理端通知渠道、规则、任务列表、重试、重发、日志查看接口
- 钉钉收件目录重建与收件人解析链路
- 站内信列表、已读/未读状态更新
- 通知设置页的规则保存、渠道保存、历史筛选与日志展开
- 页面真实渲染和 tab 切换

以下内容不在本轮测试核心范围：

- 钉钉 / 邮件真实外部网络发送成功率
- 未触达的其他页面视觉回归
- 非通知域的全站权限与路由回归

## Environment

- 平台：Windows PowerShell，本地仓库 `D:\ProjectPackage\RagflowAuth`
- 后端：Python 3.12，pytest，可通过 `ensure_schema` 初始化测试库
- 前端：Node.js + npm，CRA/Jest 环境
- 真实浏览器：Playwright CLI
- 若执行真实浏览器验证，需要本地启动后端和前端服务

## Accounts and Fixtures

- 后端单测使用临时 SQLite 数据库和现有测试桩
- 前端测试使用 Jest mock 的 `notificationApi`
- 浏览器验证使用本地管理员账号；若仓库文档已有默认管理员凭据，则以文档为准
- 若真实登录凭据或本地启动条件缺失，测试必须直接失败并记录前置条件缺口

## Commands

- `python -m pytest backend/tests/test_notification_dispatch_unit.py backend/tests/test_admin_notifications_api_unit.py backend/tests/test_inbox_api_unit.py backend/tests/test_notification_recipient_map_rebuild_unit.py`
  - 期望：全部通过，证明投递、管理端接口、站内信与钉钉目录重建回归稳定
- `python -m pytest backend/tests/test_notification_dingtalk_adapter_unit.py backend/tests/test_operation_approval_notification_migration_unit.py`
  - 期望：全部通过，证明适配器与通知耦合回归未受破坏
- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/notification/api.test.js src/features/notification/settings/useNotificationSettingsPage.test.js src/pages/NotificationSettings.test.js src/features/notification/messages/useMessagesPage.test.js src/pages/InboxPage.test.js`
  - 期望：全部通过，通知设置和站内信读取页面无回归
- `npx --yes --package @playwright/cli playwright-cli ...`
  - 期望：能在真实浏览器打开通知设置页、完成登录、切换标签，并生成截图证据

## Test Cases

### T1: 后端通知 facade / repository / service 回归

- Covers: P1-AC1, P1-AC2, P1-AC3, P3-AC1
- Level: unit / integration
- Command: `python -m pytest backend/tests/test_notification_dispatch_unit.py backend/tests/test_admin_notifications_api_unit.py backend/tests/test_inbox_api_unit.py backend/tests/test_notification_recipient_map_rebuild_unit.py`
- Expected: 所有用例通过，通知渠道、规则、投递、站内信和管理端 API 行为与重构前一致

### T2: 通知适配器与跨域耦合回归

- Covers: P1-AC2, P1-AC3, P3-AC1
- Level: unit
- Command: `python -m pytest backend/tests/test_notification_dingtalk_adapter_unit.py backend/tests/test_operation_approval_notification_migration_unit.py`
- Expected: 适配器与审批迁移相关通知路径保持稳定

### T3: 前端通知设置 hook / 页面回归

- Covers: P2-AC1, P2-AC2, P2-AC3, P3-AC2
- Level: unit / component
- Command: `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/notification/api.test.js src/features/notification/settings/useNotificationSettingsPage.test.js src/pages/NotificationSettings.test.js src/features/notification/messages/useMessagesPage.test.js src/pages/InboxPage.test.js`
- Expected: hook、页面壳层、API 适配和 inbox 相关回归通过

### T4: 通知设置页真实浏览器验证

- Covers: P2-AC2, P2-AC3, P3-AC2, P3-AC3
- Level: e2e
- Command: `npx --yes --package @playwright/cli playwright-cli ...`
- Expected: 能成功登录、打开通知设置页、切换 `rules/channels/history` 标签，并留下截图或同等级证据

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend notification | facade / store split with admin + inbox regression | unit/integration | P1-AC1, P1-AC2, P1-AC3, P3-AC1 | `test-report.md#T1` |
| T2 | backend notification | adapter and coupled notification paths remain stable | unit | P1-AC2, P1-AC3, P3-AC1 | `test-report.md#T2` |
| T3 | frontend notification | settings hook/page and inbox-related Jest regression | unit/component | P2-AC1, P2-AC2, P2-AC3, P3-AC2 | `test-report.md#T3` |
| T4 | notification UI | real browser render and tab switching | e2e/manual | P2-AC2, P2-AC3, P3-AC2, P3-AC3 | `test-report.md#T4` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: pytest, npm, react-scripts test, playwright, playwright-cli
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 使用真实仓库和本地运行时；只要页面交互在范围内，就必须使用真实浏览器并记录证据
- Escalation rule: 未形成初始结论前，不查看 `execution-log.md` 和 `task-state.json`

## Pass / Fail Criteria

- Pass when:
  - T1、T2、T3、T4 全部通过
  - 没有因为重构引入新的 payload 结构变化、接口错误码变化或页面交互回归
  - `test-report.md` 记录了命令、结果和证据路径
- Fail when:
  - 任一关键命令失败
  - 通知渠道 / 规则 / 投递 / 站内信行为与既有测试基线不一致
  - 页面测试或浏览器验证出现缺失元素、tab 切换异常、控制台错误或无法登录

## Regression Scope

- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/inbox/router.py`
- `backend/services/notification/*`
- `fronted/src/features/notification/api.js`
- `fronted/src/features/notification/messages/useMessagesPage.js`
- `fronted/src/pages/InboxPage.js`
- 与通知耦合的 `operation_approval` 通知迁移回归

## Reporting Notes

- 结果写入 `test-report.md`
- 浏览器截图、日志等非任务工件证据落到 `output/playwright/`
- 若缺少启动条件、账号或工具，必须在 `test-report.md` 和 `task-state.json.blocking_prereqs` 明确写明，不允许跳过或伪造通过
