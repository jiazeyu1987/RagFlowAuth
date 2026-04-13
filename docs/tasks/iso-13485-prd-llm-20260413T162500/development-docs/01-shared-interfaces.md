# 共享接口与冻结契约

## 目的

本文件是多 LLM 并行开发时的共享冻结层。不同工作流不得各自发明新的能力名、路由前缀、事件名、通知载荷或核心实体名。

## 路由前缀 owner

| 路由前缀 | owner | 说明 |
| --- | --- | --- |
| `/quality-system` | `WS02` | 体系文件工作台根入口 |
| `/quality-system/doc-control` | `WS01` | 受控文件与文控流程 |
| `/quality-system/training` | `WS03` | 培训知晓与问题闭环 |
| `/quality-system/change-control` | `WS04` | 变更台账与执行计划 |
| `/quality-system/equipment` | `WS05` | 设备主档与生命周期 |
| `/quality-system/batch-records` | `WS06` | 批记录模板与执行 |
| `/quality-system/audit` | `WS07` | 审计、证据导出、日志 |
| `/quality-system/governance-closure` | `WS08` | 投诉、CAPA、内审、管理评审 |

## 能力资源名 owner

以下资源名冻结，由 `WS02` 统一落到 `capabilities.js` 和 `permission_models.py`：

- `quality_system`
- `document_control`
- `training_ack`
- `change_control`
- `equipment_lifecycle`
- `metrology`
- `maintenance`
- `batch_records`
- `audit_events`
- `complaints`
- `capa`
- `internal_audit`
- `management_review`

## 核心实体 owner

| 实体 | owner | 说明 |
| --- | --- | --- |
| `ControlledDocument` | `WS01` | 文件主档 |
| `ControlledRevision` | `WS01` | 文件版本、审批、生效、作废 |
| `TrainingAssignment` | `WS03` | 培训任务 |
| `QualityQuestionThread` | `WS03` | 有疑问闭环消息线程 |
| `ChangeRequest` | `WS04` | 变更主单 |
| `ChangePlanItem` | `WS04` | 变更节点计划 |
| `EquipmentAsset` | `WS05` | 设备资产 |
| `MetrologyRecord` | `WS05` | 计量记录 |
| `MaintenanceRecord` | `WS05` | 维护保养记录 |
| `BatchRecordTemplate` | `WS06` | 批记录模板 |
| `BatchRecordExecution` | `WS06` | 批记录执行单 |
| `QualityAuditEvent` | `WS07` | 审计事件统一结构 |
| `ComplaintCase` | `WS08` | 投诉/反馈主单 |
| `CapaAction` | `WS08` | CAPA 行动项 |
| `InternalAuditRecord` | `WS08` | 内审记录 |
| `ManagementReviewRecord` | `WS08` | 管理评审记录 |

## 通知载荷契约

通知结构由 `WS03` 维护，其他工作流只按此结构发消息：

- `event_type`
- `title`
- `body`
- `recipient_user_ids`
- `link_path`
- `resource_type`
- `resource_id`
- `due_at_ms`
- `meta`

推荐事件类型：

- `controlled_revision_effective`
- `controlled_revision_obsolete`
- `training_assignment_created`
- `training_question_submitted`
- `change_plan_due_soon`
- `equipment_due_soon`
- `metrology_due_soon`
- `maintenance_due_soon`
- `batch_record_pending_sign`

## 审计事件契约

审计结构由 `WS07` 维护，其他工作流只埋点，不重定义字段：

- `action`
- `source`
- `resource_type`
- `resource_id`
- `event_type`
- `actor`
- `created_at_ms`
- `before`
- `after`
- `reason`
- `signature_id`
- `request_id`
- `meta`

推荐事件域：

- 文控：`document_control`
- 培训：`training_ack`
- 变更：`change_control`
- 设备：`equipment_lifecycle`
- 批记录：`batch_records`
- 搜索/对话：`global_search`、`smart_chat`

## 证据附件契约

通用证据引用结构由 `WS07` 维护：

- `attachment_id`
- `resource_type`
- `resource_id`
- `filename`
- `mime_type`
- `storage_ref`
- `uploaded_by`
- `uploaded_at_ms`
- `evidence_role`

`WS06` 可在此基础上扩展批记录现场照片字段，但不能改通用主键结构。

## 变更共享规则

1. 任何共享契约变更，都必须先改本文件。
2. 共享契约一旦变更，受影响工作流必须同步更新各自文档。
3. 未在本文件冻结的共享项，不得默认进入代码实现。
