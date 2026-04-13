# WS03：培训知晓、15 分钟确认与站内信闭环

- Workstream ID: `WS03`
- 推荐 owner：全栈
- 独立性：中高

## 目标

实现源 PRD 中“生效文件触发培训、阅读 15 分钟、已知晓/有疑问、站内信提问闭环、培训记录可审计”的完整链路。

## 来源需求

- 源 PRD 问题项：`TR-01`
- 源 PRD 章节：培训与知晓确认、建议的核心台账/实体

## 负责边界

- `TrainingAssignment`
- `QualityQuestionThread`
- 培训任务创建、阅读计时、知晓确认、疑问提问与处理结果
- 培训相关站内信、催办和逾期状态
- 培训完成记录、文件版本关联和人员留痕

## 不负责范围

- 不负责受控文件主根和文档生命周期定义。
- 不负责 `体系文件` 导航和权限资源名设计。
- 不负责变更、设备、批记录。

## 代码写入边界

后端 owner：

- `backend/app/modules/training_compliance/*`
- `backend/services/training_compliance.py`
- `backend/services/training_compliance_*`
- `backend/app/modules/inbox/*`
- `backend/services/notification/*`
- `backend/services/inbox_service.py`

前端 owner：

- `fronted/src/features/trainingCompliance/*`
- `fronted/src/features/notification/*`
- `fronted/src/features/operationApproval/useInboxPage.js`
- `fronted/src/pages/TrainingComplianceManagement.js`
- `fronted/src/pages/InboxPage.js`

允许新增：

- `fronted/src/features/qualitySystem/training/*`
- `backend/app/modules/training_ack/*`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/shared/auth/capabilities.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`

## 共享接口

本工作流拥有：

- 通知 payload 结构
- 培训相关 `event_type`
- `TrainingAssignment`
- `QualityQuestionThread`

本工作流消费：

- `WS01` 的 `ControlledRevision` 与 `controlled_revision_effective`
- `WS02` 的 `training_ack` 能力资源名
- `WS07` 的审计事件 schema

## 依赖关系

- 需要 `WS01` 先冻结文档生效事件。
- 需要 `WS02` 先冻结能力资源名和入口路由。

## 验收标准

- 生效文件可以生成培训任务。
- 培训支持最短阅读时长约束。
- 用户必须在 `已知晓` 和 `有疑问` 之间显式选择。
- `有疑问` 会创建可追溯的站内信闭环。
- 培训记录能回溯到文件版本、人员、时间、结果。

## 交接给 LLM 的规则

1. 只在本工作流 own 的模块里做培训与消息闭环。
2. 所有通知字段必须复用共享 payload 结构。
3. 不重定义文档状态，只消费 `WS01` 输出。
4. 审计埋点字段按 `WS07` 输出，不单独扩充主字段。
