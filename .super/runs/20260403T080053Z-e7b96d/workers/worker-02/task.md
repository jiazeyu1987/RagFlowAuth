# worker-02 Task

## Goal

验证通知模块前端实现是否完整。重点覆盖通知设置页、消息中心页、路由/导航接入、API 调用与交互闭环。

## Owned Paths

- `.super/runs/20260403T080053Z-e7b96d/workers/worker-02/`

## Do Not Modify

- 不要修改仓库业务代码文件。
- 不要修改其他 worker 目录。
- 你不是单独在代码库工作，禁止回滚或覆盖他人改动。

## Dependencies

- 可读取前端相关文件（只读）：
- `fronted/src/features/notification/api.js`
- `fronted/src/pages/NotificationSettings.js`
- `fronted/src/pages/Messages.js`
- `fronted/src/components/Layout.js`
- `fronted/src/App.js`
- `fronted/e2e/tests/review.notification.spec.js`
- `fronted/e2e/tests/messages.center.spec.js`
- 可执行验证命令（只读验证）：
- `npm run build`（cwd=`fronted`）

## Acceptance Criteria

- 在 `progress.md` 记录：开始、关键里程碑、阻塞（如有）、ready_for_validation。
- 在 `state.json` 同步更新 `status/current_step/updated_at`。
- 生成 `frontend-validation.md`，内容必须包含：
- 页面/交互核对清单（通知设置 + 消息中心）
- 路由与导航可达性验证
- 构建命令与结果
- Findings（按严重级别排序，含文件路径+原因）
- 结论（是否满足“前端通知模块改造要求”）
- 完成后将 `state.json.status` 置为 `ready_for_validation`。

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- 只做验证与结论输出，不做功能开发。
