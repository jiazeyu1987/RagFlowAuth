# WS04：变更控制台账、计划与关闭确认

- Workstream ID: `WS04`
- 推荐 owner：全栈偏后端
- 独立性：中

## 目标

把源 PRD 中的变更控制要求从现有紧急变更能力扩展为“发起、评估、计划、执行、提醒、跨部门确认、自动回台账、文控联动”的完整台账工作流。

## 来源需求

- 源 PRD 问题项：`CC-01`
- 源 PRD 章节：变更控制、建议的核心台账/实体、整改实施路线图 `R4`

## 负责边界

- `ChangeRequest`
- `ChangePlanItem`
- 变更主单、计划节点、到期提醒、完成确认、关闭结果
- 变更与受控文件、设备、批记录的关联关系
- 关闭后自动回到台账

## 不负责范围

- 不负责受控文件本体实现。
- 不负责入口导航与能力名。
- 不负责通用通知结构和通用审计 schema。

## 代码写入边界

后端 owner：

- `backend/app/modules/emergency_changes/*`
- `backend/services/emergency_change.py`

前端 owner：

- `fronted/src/features/changeControl/*`
- `fronted/src/pages/ChangeControl.js`

允许新增：

- `backend/app/modules/change_control/*`
- `backend/services/change_control/*`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`
- `backend/services/compliance/*`

## 共享接口

本工作流拥有：

- `ChangeRequest`
- `ChangePlanItem`
- 变更状态枚举和计划节点状态

本工作流消费：

- `WS01` 的 `ControlledRevision` 关联契约
- `WS02` 的 `change_control` 能力名和子路由
- `WS03` 的提醒/通知 payload
- `WS07` 的审计事件 schema

## 依赖关系

- 依赖 `WS01` 冻结文档关联结构。
- 依赖 `WS02` 提供入口与权限壳层。
- 依赖 `WS07` 提供统一审计字段。

## 验收标准

- 变更可完整记录发起、评估、计划、执行、确认、关闭。
- 到期前可提醒责任人。
- 计划完成后可流转到其他部门确认。
- 关闭结果会自动回写台账。
- 变更可挂接受控文件更新，不再停留在口头状态。

## 交接给 LLM 的规则

1. 若需要提醒能力，直接消费 `WS03` 的通知结构，不自造消息 schema。
2. 受控文件字段和版本引用只消费 `WS01` 契约。
3. 不直接改入口导航，只向 `WS02` 申请子路由接入。
4. 若要扩充审计字段，先走 `WS07` 共享契约更新。
