# WS05：设备全生命周期、计量与维护保养

- Workstream ID: `WS05`
- 推荐 owner：全栈偏后端
- 独立性：高

## 目标

实现源 PRD 中“设备采购到报废、计量、维护保养、到期提醒、审批、导出、审计”的完整设备台账能力，作为前期重点工作流之一。

## 来源需求

- 源 PRD 问题项：`EQ-01`、`MT-01`、`MA-01`
- 源 PRD 章节：设备、计量、维护保养、整改实施路线图 `R3`

## 负责边界

- `EquipmentAsset`
- `MetrologyRecord`
- `MaintenanceRecord`
- 采购、验收、投用、使用、维护、计量、报废状态机
- 到期提醒、附件、确认审批、导出

## 不负责范围

- 不负责入口导航和能力名。
- 不负责培训和变更流程。
- 不负责通用审计 schema。

## 代码写入边界

允许新增后端：

- `backend/app/modules/equipment/*`
- `backend/app/modules/metrology/*`
- `backend/app/modules/maintenance/*`
- `backend/services/equipment/*`
- `backend/services/metrology/*`
- `backend/services/maintenance/*`

允许新增前端：

- `fronted/src/features/equipment/*`
- `fronted/src/features/metrology/*`
- `fronted/src/features/maintenance/*`
- `fronted/src/pages/EquipmentLifecycle.js`
- `fronted/src/pages/MetrologyManagement.js`
- `fronted/src/pages/MaintenanceManagement.js`

禁止主动修改：

- `fronted/src/routes/routeRegistry.js`
- `backend/app/core/permission_models.py`
- `backend/app/modules/audit/*`
- `backend/services/compliance/*`

## 共享接口

本工作流拥有：

- `EquipmentAsset`
- `MetrologyRecord`
- `MaintenanceRecord`
- 设备状态机

本工作流消费：

- `WS02` 的 `equipment_lifecycle`、`metrology`、`maintenance` 能力名与子路由
- `WS03` 的提醒/通知 payload
- `WS07` 的通用附件与审计结构

## 依赖关系

- 可与 `WS01`、`WS02` 并行启动。
- 依赖 `WS02` 完成入口接入。
- 依赖 `WS03` 的提醒 payload 和 `WS07` 的审计字段。

## 验收标准

- 设备主档覆盖采购到报废全过程。
- 计量与维护记录支持附件、确认、审批。
- 到期前能提醒责任人。
- 记录支持导出与审计留痕。

## 交接给 LLM 的规则

1. 尽量在新增目录中实现，避免侵入其他现有模块。
2. 提醒能力直接复用共享通知结构。
3. 附件与证据引用走 `WS07` 定义，不自造附件主键。
4. 若需要权限接入，只通过 `WS02` 冻结的资源名接入。
