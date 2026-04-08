# 通知模块重构一期执行计划
## 文档定位

本文档是 [系统重构修改计划](./system-refactor-plan-2026-04.md) 中“阶段 3：通知模块拆分”的第一期执行版本，用于约束本轮 `notification` 前后端局部重构的边界、步骤和验收标准。

放在 `docs/exec-plans/active/` 的原因：

- 这是跨后端 `service/store/router/tests` 与前端通知设置页的持续执行计划，不是单点技术债记录
- 它需要跟随任务工件、验证结果和阶段状态持续更新，不适合只放到 `docs/tasks/`
- 它是系统重构路线中的阶段实施文档，粒度高于单次执行任务

## 背景与目标

当前通知域同时存在后端与前端两个热点：

- `backend/services/notification/service.py` 约 957 行，同时承载渠道管理、规则管理、收件人解析、任务入队、任务分发、重试重发、站内信已读更新、钉钉目录重建和审计写入
- `backend/services/notification/store.py` 约 672 行，同时承载渠道、规则、任务、投递日志、站内信列表与读状态的全部持久化逻辑
- `fronted/src/features/notification/settings/useNotificationSettingsPage.js` 约 365 行，同时承载渠道表单、规则矩阵、历史筛选、日志展开和任务动作
- `fronted/src/pages/NotificationSettings.js` 约 553 行，同时承载页面壳层、三块业务区、格式化、筛选和操作按钮

一期目标不是重写通知系统，而是在不改变对外 API、任务状态语义和页面交互的前提下，把通知域从“继续加需求风险很高”的状态收敛到“职责清楚、可继续局部演进”的状态。

## 当前问题边界

### 1. `NotificationManager` 是事实上的超级服务

当前 `service.py` 同时负责：

- 通道配置读写与审计
- 规则播种、规则读取、规则保存
- 收件人标准化与地址解析
- 任务去重、创建、分发、重试、重发
- 站内信列表、读状态更新、全部已读
- 钉钉目录重建、用户绑定同步
- 审计事件发出

这意味着任意通知需求变更几乎都会继续扩大同一个文件。

### 2. `NotificationStore` 混合了多类持久化职责

当前 `store.py` 同时覆盖：

- notification channel 读写
- notification event rule 读写
- notification job 读写与查询
- delivery log 写入与读取
- inbox 列表与读状态更新

这会导致后续只想修改一类表访问逻辑时，也必须继续进入同一个超大 store。

### 3. 前端通知设置页的状态域过重

当前 `useNotificationSettingsPage.js` 同时负责：

- 页面初始化加载
- 渠道表单构建与校验
- 规则矩阵切换与保存
- 历史筛选与查询
- 任务重试、重发、分发
- 日志懒加载和展开状态

而 `NotificationSettings.js` 同时承载：

- tab 切换
- rules / channels / history 三个大区块的完整展示
- 通用格式化与标签文案
- 任务操作按钮

这使得很小的改动也会同时波及 hook 和页面。

## 本期范围

### 纳入范围

- `backend/services/notification/service.py`
- `backend/services/notification/store.py`
- `backend/services/notification/__init__.py`
- `backend/services/notification/repositories/*`
- `backend/services/notification/*_service.py`
- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/inbox/router.py`
- `fronted/src/features/notification/settings/*`
- `fronted/src/pages/NotificationSettings.js`
- 通知相关前后端测试与任务工件

### 明确不在本期范围

- 不修改通知 API 路径和返回 envelope
- 不修改通知 schema、事件类型、任务状态或投递规则
- 不引入 fallback、兼容分支或静默降级
- 不大改 `InboxPage` 和 `useMessagesPage` 结构，除非本次收敛需要最小配合
- 不扩散到审批、权限、路由注册和全站 UI 重做

## 不可破坏的外部契约

### 1. 通知服务公开入口保持稳定

以下符号本期不能失效：

- `NotificationManager`
- `NotificationService`
- `NotificationManagerError`
- `NotificationServiceError`
- `NotificationStore`

原因是这些符号已经通过 `backend/services/notification/__init__.py` 暴露，并被依赖注入、router 和测试使用。

### 2. 管理端与站内信 API 契约保持稳定

以下接口的路径、响应 envelope 和错误传播语义保持不变：

- `GET /admin/notifications/channels`
- `PUT /admin/notifications/channels/{channel_id}`
- `POST /admin/notifications/channels/{channel_id}/recipient-map/rebuild-from-org`
- `GET /admin/notifications/rules`
- `PUT /admin/notifications/rules`
- `GET /admin/notifications/jobs`
- `GET /admin/notifications/jobs/{job_id}/logs`
- `POST /admin/notifications/jobs/{job_id}/retry`
- `POST /admin/notifications/jobs/{job_id}/resend`
- `POST /admin/notifications/dispatch`
- `GET /me/messages`
- `PATCH /me/messages/{job_id}/read-state`
- `POST /me/messages/mark-all-read`

### 3. 前端通知设置页选择器与行为保持稳定

本期优先保留现有：

- `data-testid`
- tab key：`rules` / `channels` / `history`
- 规则保存、渠道保存、历史筛选、日志展开、重试、重发和分发操作行为

## 目标结构

一期结束后，目标结构如下：

```text
backend/services/notification/
  __init__.py
  service.py                      # 稳定 facade，只做依赖装配与委托
  store.py                        # 稳定 facade，只保留仓储聚合入口
  audit.py                        # 审计发出辅助
  channel_service.py              # 渠道管理
  event_rule_service.py           # 规则管理
  dispatch_service.py             # 入队、分发、重试、重发
  inbox_service.py                # 站内信列表与读状态
  recipient_directory_service.py  # 钉钉目录重建与用户绑定同步
  repositories/
    __init__.py
    channel_repository.py
    event_rule_repository.py
    job_repository.py
    delivery_log_repository.py
    inbox_repository.py

fronted/src/features/notification/settings/
  helpers.js
  useNotificationChannelSettings.js
  useNotificationRuleSettings.js
  useNotificationHistory.js
  useNotificationSettingsPage.js   # 组合式 hook
  components/
    NotificationSettingsHeader.js
    NotificationRulesSection.js
    NotificationChannelsSection.js
    NotificationHistorySection.js
```

说明：

- `NotificationManager` / `NotificationService` 继续保留公开方法，但内部退化为 facade
- `NotificationStore` 继续保留为公开入口，但内部不再直接承载全部 SQL 细节
- 前端页面只负责 tab 和区块组装，业务状态拆到更单一的 hook

## 拆分步骤

### 1. 先拆后端仓储，保留 `NotificationStore` 外壳

目标：

- 让 `store.py` 不再直接承载所有通知表读写细节

具体动作：

- 新增 `repositories/channel_repository.py`
- 新增 `repositories/event_rule_repository.py`
- 新增 `repositories/job_repository.py`
- 新增 `repositories/delivery_log_repository.py`
- 新增 `repositories/inbox_repository.py`
- `NotificationStore` 保留 `db_path`、`_conn()` 和对外兼容方法，但实现改为委托仓储

### 2. 再拆 `NotificationManager` 分域服务

目标：

- 把渠道、规则、分发、站内信、钉钉目录重建职责从单个服务类中拆出

具体动作：

- 新增 `channel_service.py`
- 新增 `event_rule_service.py`
- 新增 `dispatch_service.py`
- 新增 `inbox_service.py`
- 新增 `recipient_directory_service.py`
- `service.py` 仅保留 facade 和稳定公开方法

### 3. 收敛审计与收件人解析辅助逻辑

目标：

- 避免静态 helper 继续散落在主服务里

具体动作：

- 把审计写入辅助提到独立 `audit.py`
- 把收件人标准化、channel type 规整、地址解析和适配器选择聚合到分域服务内部

### 4. 拆前端通知设置页状态域

目标：

- 把页面回到“组装 UI”，把 hook 回到“单一状态域”

具体动作：

- 把表单/规则/历史相关 helper 提到 `helpers.js`
- 把渠道配置逻辑拆到 `useNotificationChannelSettings.js`
- 把规则逻辑拆到 `useNotificationRuleSettings.js`
- 把投递历史与任务动作拆到 `useNotificationHistory.js`
- `useNotificationSettingsPage.js` 改成组合 hook

### 5. 拆前端展示区块

目标：

- 缩小 `NotificationSettings.js`

具体动作：

- 页面头部、规则区、渠道区、历史区拆成独立组件
- 保持现有 `data-testid` 和行为契约

### 6. 最后补齐测试和任务证据

目标：

- 证明这轮重构没有改变行为

具体动作：

- 跑通知相关后端 pytest
- 跑通知相关前端 Jest
- 做真实浏览器通知设置页验证
- 把命令、结果和证据写入任务工件

## 测试与验证计划

### 后端

- `python -m pytest backend/tests/test_notification_dispatch_unit.py backend/tests/test_admin_notifications_api_unit.py backend/tests/test_inbox_api_unit.py backend/tests/test_notification_recipient_map_rebuild_unit.py`
- `python -m pytest backend/tests/test_notification_dingtalk_adapter_unit.py backend/tests/test_operation_approval_notification_migration_unit.py`

### 前端

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/features/notification/api.test.js src/features/notification/settings/useNotificationSettingsPage.test.js src/pages/NotificationSettings.test.js src/features/notification/messages/useMessagesPage.test.js src/pages/InboxPage.test.js`

### 浏览器

- 启动本地前后端后，用 Playwright CLI 打开通知设置页，完成登录、tab 切换，并保存截图证据到 `output/playwright/`

## 风险与回滚

### 主要风险

- facade 委托改造后若遗漏公开方法，会影响依赖注入或 router
- 分发逻辑拆分时若打乱“入队 -> 日志 -> 分发/重试/重发”时序，可能导致任务状态回归
- 前端拆组件时若改变 `data-testid` 或字段映射，会造成 Jest 回归失真

### 回滚策略

- 先保留公开 facade 和方法签名，只替换内部实现
- 以仓储和分域服务的引入为主，不在同一轮顺手改业务规则
- 前端优先保持页面结构和测试选择器稳定，必要时通过组合 hook 先收敛职责

## 完成标准

满足以下条件即可认为一期完成：

1. `backend/services/notification/store.py` 显著缩小，并主要承担 facade / repository 聚合职责
2. `backend/services/notification/service.py` 显著缩小，并主要承担 facade / 委托职责
3. 通知投递、规则管理、站内信读状态和钉钉目录重建有清晰分域服务边界
4. `useNotificationSettingsPage.js` 不再同时承载所有状态域
5. `NotificationSettings.js` 明显缩小，按区块拆成独立展示组件
6. 通知相关后端、前端与真实浏览器验证通过
