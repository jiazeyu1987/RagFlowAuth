# 维护计划

版本: v1.0
更新时间: 2026-04-14
适用条目: GBZ-01
当前环境: release 2.0.0
计划覆盖变更类别: os, database, api, config, intended_use
维护责任人: 运维负责人
QA复核人: QA负责人
下次维护计划复核日期: 2026-10-14
仓库外残余项: 线下维护审批单、执行签字和培训签到仍需在线下受控体系归档

## 1. 目标

在维护阶段持续判断变更是否影响已确认状态，并在需要时触发再确认、更新验证计划/报告和追踪矩阵。

## 2. 维护影响判定输入

- 当前受控文档：`docs/compliance/intended_use.md`、`docs/compliance/traceability_matrix.md`、`docs/compliance/validation_plan.md`、`docs/compliance/validation_report.md`
- 代码内配置变更日志：`config_change_logs`
- 当前发布版本基线：`release 2.0.0`

## 3. 再确认触发器

| 变更类别 | 触发条件 | 处理要求 |
|---|---|---|
| os | 操作系统版本、补丁级别或运行环境基线变化 | 必须执行维护影响判定并重新确认 |
| database | 数据库引擎、路径、结构或隔离策略变化 | 必须执行维护影响判定并重新确认 |
| api | 外部接口、关键路由或审批/通知/审计接口变化 | 必须执行维护影响判定并重新确认 |
| config | `upload_allowed_extensions`、`data_security_settings` 等受控配置变化 | 必须执行维护影响判定；命中受控域时重新确认 |
| intended_use | 预期用途版本或边界变化 | 必须阻断继续沿用旧验证结论，并重新确认 |

## 4. 执行要求

1. 变更前先完成维护影响判定。
2. 维护影响判定必须引用 `docs/compliance/traceability_matrix.md` 作为输入。
3. 命中再确认触发器后，必须更新验证计划、验证报告和相关受控文档。
4. 只有在维护验证闭环完成后，维护项才可视为 `closed`。
