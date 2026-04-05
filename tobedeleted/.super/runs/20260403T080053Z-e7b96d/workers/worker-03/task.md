# worker-03 Task

## Goal

验证通知能力是否已形成“独立模块”，并给出结构化判定：完全独立 / 部分独立 / 非独立。

## Owned Paths

- `.super/runs/20260403T080053Z-e7b96d/workers/worker-03/`

## Do Not Modify

- 不要修改仓库业务代码文件。
- 不要修改其他 worker 目录。
- 你不是单独在代码库工作，禁止回滚或覆盖他人改动。

## Dependencies

- 可读取（只读）：
- `backend/services/notification/`
- `backend/app/modules/admin_notifications/router.py`
- `backend/app/modules/me/router.py`
- `backend/app/dependencies.py`
- `backend/services/approval/service.py`
- `backend/services/operation_approval/service.py`
- `fronted/src/features/notification/`
- `fronted/src/pages/NotificationSettings.js`
- `fronted/src/pages/Messages.js`
- `fronted/src/App.js`
- `fronted/src/components/Layout.js`

## Acceptance Criteria

- 在 `progress.md` 记录：开始、关键里程碑、阻塞（如有）、ready_for_validation。
- 在 `state.json` 同步更新 `status/current_step/updated_at`。
- 生成 `independence-validation.md`，内容必须包含：
- 依赖图（模块输入/输出，谁调用通知模块）
- 耦合点清单（运行时依赖、跨模块共享模型、不可替换点）
- 独立性判定（完全独立/部分独立/非独立）与证据
- 如为“部分独立/非独立”，给出最小解耦建议（不改代码，仅建议）
- 完成后将 `state.json.status` 置为 `ready_for_validation`。

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- 只做验证与结论输出，不做功能开发。
