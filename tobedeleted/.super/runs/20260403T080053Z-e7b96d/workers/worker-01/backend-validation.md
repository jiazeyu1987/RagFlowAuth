# worker-01 backend validation

## 验证范围

- `backend/services/notification/service.py`
- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/me/router.py`
- `backend/app/dependencies.py`
- `backend/services/approval/service.py`

## 执行命令与结果

- 命令: `python -m unittest backend.tests.test_notification_dispatch_unit backend.tests.test_admin_notifications_api_unit backend.tests.test_me_messages_api_unit backend.tests.test_review_notification_integration_unit`
- 结果: `Ran 10 tests in 2.172s`，`OK`

## Findings

1. [P2] `backend/services/approval/service.py:377-402`
   - `_notify_non_blocking()` 会捕获 `service.notify_event()` 和 `service.dispatch_pending()` 的所有异常，只写 warning，不向调用方返回失败。
   - 这意味着审批流中的通知准备和投递失败会被静默压下，和“严格 no-fallback / fail-fast”策略不一致。

2. [P2] `backend/services/notification/service.py:290-313`
   - `dispatch_pending()` 对每个 job 的异常做了 `except Exception`，然后把该 job 伪装成 `status: "error"` 的返回项。
   - 这让批量调度调用方无法通过异常边界感知失败，只能依赖返回内容，属于显式的非 fail-fast 路径。

## 结论

- 通知主链路、管理端 API、站内信 API、依赖注入和审计埋点都已实现，单测通过。
- 但按本次验证口径，后端**不完全符合**严格 no-fallback 策略，因为审批通知和批量派发都存在吞异常的非阻塞路径。
- 如果验收标准允许这类非阻塞通知设计，那么功能链路可视为可用；如果必须严格 fail-fast，则需要移除上述吞异常逻辑后再复验。
