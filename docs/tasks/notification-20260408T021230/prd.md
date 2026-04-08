# Notification Refactor PRD

- Task ID: `notification-20260408T021230`
- Created: `2026-04-08T02:12:30`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `继续推进系统前后端重构，完成 notification 模块第一期局部重构，保持现有行为与接口契约稳定`

## Goal

把 `notification` 域从“超大 service + 超大 store + 超大前端页面/Hook”收敛为可继续演进的局部结构，在不改变现有 API 路径、返回 envelope、页面交互语义和消息投递规则的前提下，降低通知渠道配置、规则管理、任务投递和站内信状态维护的耦合度。

## Scope

- `backend/services/notification/service.py`
- `backend/services/notification/store.py`
- `backend/services/notification/__init__.py`
- `backend/services/notification/*`
- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/inbox/router.py`
- `backend/tests/test_notification_dispatch_unit.py`
- `backend/tests/test_admin_notifications_api_unit.py`
- `backend/tests/test_inbox_api_unit.py`
- `backend/tests/test_notification_recipient_map_rebuild_unit.py`
- `fronted/src/features/notification/settings/*`
- `fronted/src/pages/NotificationSettings.js`
- `fronted/src/pages/NotificationSettings.test.js`
- `fronted/src/features/notification/settings/useNotificationSettingsPage.test.js`
- 需要配合的通知相关 API / 页面回归验证与任务工件

## Non-Goals

- 不修改 `/api/admin/notifications/*` 和 `/api/me/messages/*` 的路径与 envelope
- 不修改通知数据库 schema、事件类型枚举、任务状态语义、重试与重发业务规则
- 不重写 `InboxPage` / `useMessagesPage`，除非本次后端边界调整需要最小配合改动
- 不引入 fallback、兼容分支、静默降级或 mock 返回
- 不扩散到 `operation_approval`、权限系统、路由注册或全局样式重做

## Preconditions

- `backend/database/schema/ensure.py` 能正常初始化通知相关表
- 本地 Python、Node.js、npm、pytest、Jest 可运行
- Playwright CLI 可用于真实浏览器验证
- 若进行真实页面验证，本地后端和前端可启动，且管理员账号可登录
- 若任一前置条件缺失，必须停止执行并记录到 `task-state.json.blocking_prereqs`

## Impacted Areas

- `backend/app/dependencies.py` 中的 `notification_manager` / `notification_service` 装配与公开接口
- `backend/app/modules/admin_notifications/router.py` 对 `NotificationManager` 的调用
- `backend/app/modules/inbox/router.py` 对站内信读状态接口的调用
- 依赖通知事件写入、投递和站内信读取的回归测试
- `fronted/src/features/notification/api.js` 提供的数据结构与页面消费方式
- `fronted/src/pages/NotificationSettings.js` 中的 `data-testid`、表单交互与历史记录操作

## Phase Plan

### P1: 后端通知职责拆分

- Objective: 把 `NotificationStore` 收敛为 facade，把 `NotificationManager` 收敛为编排入口，拆出仓储和分域服务，同时保持公开接口稳定。
- Owned paths:
  - `backend/services/notification/service.py`
  - `backend/services/notification/store.py`
  - `backend/services/notification/__init__.py`
  - `backend/services/notification/repositories/*`
  - `backend/services/notification/*_service.py`
  - `backend/app/modules/admin_notifications/router.py`
  - `backend/app/modules/inbox/router.py`
  - 通知相关后端测试
- Dependencies:
  - 现有通知 schema 与 adapter
  - 现有 router 契约与依赖注入装配
- Deliverables:
  - 仓储层按渠道 / 规则 / 任务 / 投递日志 / 站内信拆分
  - `NotificationManager` 委托渠道管理、规则管理、投递、站内信、钉钉目录重建等分域服务
  - 补充至少一组 focused regression tests 锁定拆分后的关键语义

### P2: 前端通知设置页与 Hook 拆分

- Objective: 把通知设置页拆成更单一的状态域和展示区块，保留现有交互、字段和测试选择器。
- Owned paths:
  - `fronted/src/features/notification/settings/*`
  - `fronted/src/pages/NotificationSettings.js`
  - 相关前端测试
- Dependencies:
  - `fronted/src/features/notification/api.js`
  - 现有 `NotificationSettings.test.js` / hook 测试
- Deliverables:
  - 通道配置、规则矩阵、投递历史拆到独立 hook / helper / components
  - 页面壳层只保留 tab 切换与区块组装
  - 保持现有 `data-testid`、表单字段名和主要文案行为

### P3: 回归验证与工件收口

- Objective: 用后端、前端和真实浏览器三层验证证明本次重构未改变对外行为，并完成任务工件闭环。
- Owned paths:
  - `docs/exec-plans/active/notification-refactor-phase-1.md`
  - `docs/tasks/notification-20260408T021230/*`
  - `output/playwright/*`
- Dependencies:
  - P1、P2 完成
  - 可运行测试环境
- Deliverables:
  - 后端 pytest 回归记录
  - 前端 Jest 回归记录
  - 通知设置页真实浏览器证据
  - execution-log / test-report / task-state 对齐

## Phase Acceptance Criteria

### P1

- P1-AC1: `backend/services/notification/store.py` 不再直接承载全部渠道、规则、任务、投递日志、站内信读写细节，而是退化为 facade / repository 聚合入口。
- P1-AC2: `backend/services/notification/service.py` 不再直接承载全部渠道、规则、收件人解析、投递、站内信、钉钉目录重建细节，公开的 `NotificationManager` / `NotificationService` 接口保持可用。
- P1-AC3: 管理端通知 API 与站内信 API 的现有行为保持稳定，通知投递、重试、重发和读状态更新回归通过。
- Evidence expectation:
  - `execution-log.md#Phase-P1`
  - `test-report.md#T1`
  - `test-report.md#T2`

### P2

- P2-AC1: `useNotificationSettingsPage.js` 不再同时维护通道配置、规则矩阵、投递历史全部细节状态，至少拆出 helper 与分域 hook。
- P2-AC2: `NotificationSettings.js` 明显缩小，页面展示按 rules / channels / history 拆成独立展示区块或组件。
- P2-AC3: 现有通知设置页测试选择器、规则切换、渠道保存、历史筛选和日志展开行为保持稳定。
- Evidence expectation:
  - `execution-log.md#Phase-P2`
  - `test-report.md#T3`
  - `test-report.md#T4`

### P3

- P3-AC1: 通知相关后端定向回归测试通过，能够覆盖投递、规则、管理端 API、站内信读状态和钉钉目录重建。
- P3-AC2: 通知设置页相关前端测试通过，覆盖 hook 和页面壳层。
- P3-AC3: 真实浏览器下通知设置页能正常渲染、切换 tab 和展示当前配置，并有截图或等价证据落盘。
- Evidence expectation:
  - `execution-log.md#Phase-P3`
  - `test-report.md#T1`
  - `test-report.md#T2`
  - `test-report.md#T3`
  - `test-report.md#T4`

## Done Definition

- P1、P2、P3 全部完成
- 所有 acceptance ids 在 `execution-log.md` 或 `test-report.md` 中都有证据引用
- `task-state.json` 显示 `planner_review_status=approved`
- `task-state.json` 显示所有 phase 和 acceptance ids 均为 `completed`
- `test_status` 为 `passed`
- 后端 / 前端 / 浏览器验证都明确记录了命令、结果和证据位置

## Blocking Conditions

- 通知相关 schema 或依赖注入缺失，导致服务无法真实启动
- 前端 / 后端测试入口无法运行且没有可替代的真实验证路径
- Playwright 或浏览器环境不可用，但页面交互验证仍在本期范围内
- 发现需要通过 fallback、mock 或静默降级才能维持现有行为
