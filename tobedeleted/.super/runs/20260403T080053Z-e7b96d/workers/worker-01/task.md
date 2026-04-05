# worker-01 Task

## Goal

验证通知模块后端实现是否完整且符合无兜底策略。重点覆盖 `NotificationManager` 主链路、管理端 API、消息中心 API、日志与审计行为。

## Owned Paths

- `.super/runs/20260403T080053Z-e7b96d/workers/worker-01/`

## Do Not Modify

- 不要修改仓库业务代码文件。
- 不要修改其他 worker 目录。
- 你不是单独在代码库工作，禁止回滚或覆盖他人改动。

## Dependencies

- 可读取后端相关文件（只读）：
- `backend/services/notification/`
- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/me/router.py`
- `backend/app/dependencies.py`
- `backend/services/approval/service.py`
- 可执行验证命令（只读验证）：
- `python -m unittest backend.tests.test_notification_dispatch_unit backend.tests.test_admin_notifications_api_unit backend.tests.test_me_messages_api_unit backend.tests.test_review_notification_integration_unit`

## Acceptance Criteria

- 在 `progress.md` 记录：开始、关键里程碑、阻塞（如有）、ready_for_validation。
- 在 `state.json` 同步更新 `status/current_step/updated_at`。
- 生成 `backend-validation.md`，内容必须包含：
- 验证范围（功能点列表）
- 执行命令与结果
- Findings（按严重级别排序，含文件路径+原因）
- 结论（是否满足“邮件+钉钉+站内信+全链路日志”后端要求）
- 完成后将 `state.json.status` 置为 `ready_for_validation`。

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- 只做验证与结论输出，不做功能开发。
