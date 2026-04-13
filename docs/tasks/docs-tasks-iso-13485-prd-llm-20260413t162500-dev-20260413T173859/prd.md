# WS05 设备/计量/维护编码 PRD

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859`
- Created: `2026-04-13T17:38:59`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `参考 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS05-equipment-metrology-maintenance.md 开发设备全生命周期、计量与维护保养功能`

## Goal

在当前仓库中交付 `WS05` 对应的可运行代码，使设备资产主档、计量记录、维护保养记录具备可落库、可查询、可审批、可导出、可留痕、可发起临期提醒的最小闭环，并补齐可独立测试的前端管理页面。

## Scope

本次任务显式包含以下内容：

- 新增设备、计量、维护三组后端 schema、服务和 FastAPI 路由。
- 将三组服务接入 `backend/app/dependency_factory.py` 与 `backend/app/main.py`。
- 在现有通知框架中补齐 `equipment_due_soon`、`metrology_due_soon`、`maintenance_due_soon` 事件类型，使 WS05 能发出站内信提醒。
- 在现有审计框架中为设备、计量、维护的创建、状态流转、审批、提醒、导出写入标准事件。
- 新增 `fronted/src/pages/EquipmentLifecycle.js`、`fronted/src/pages/MetrologyManagement.js`、`fronted/src/pages/MaintenanceManagement.js` 及其 `features/*` 支撑代码。
- 为新增后端接口和前端页面补齐窄范围单元/组件测试。
- 更新本任务目录下的 `execution-log.md`、`test-report.md` 与 `task-state.json` 状态。

## Non-Goals

- 不修改 `fronted/src/routes/routeRegistry.js`，不负责把页面接入导航或 `quality-system` 入口。
- 不修改 `backend/app/core/permission_models.py`，不在本任务里扩展 `WS02` 拥有的 capability 模型。
- 不修改 `backend/app/modules/audit/*` 或 `backend/services/compliance/*`。
- 不实现真实文件上传存储；附件仅按 `WS07` 冻结结构保存为引用对象，不伪造上传成功路径。
- 不把通用审批中心改造成 `WS05` 的 owner；本任务只实现 WS05 自身的确认/批准动作与留痕。

## Preconditions

以下前提必须成立，缺失时应阻断而不是降级：

- 仓库可读，且 `backend/`、`fronted/`、`docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS05-equipment-metrology-maintenance.md` 均存在。
- Python 测试环境可运行 `pytest`，前端测试环境可运行 `npm test -- --watch=false --runInBand`。
- 现有通知框架 `backend/services/notification/*`、审计框架 `backend/services/audit*`、依赖装配 `backend/app/dependency_factory.py` 可修改并通过测试。
- 附件上传主服务未在仓库中落地，因此 WS05 只允许保存上游已存在的附件引用对象；若调用方无法提供引用对象，则相应记录创建应直接失败。

## Impacted Areas

- 工作流文档与共享契约：
  - `docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS05-equipment-metrology-maintenance.md`
  - `docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/01-shared-interfaces.md`
- 后端接入点：
  - `backend/app/main.py`
  - `backend/app/dependency_factory.py`
  - `backend/database/schema/ensure.py`
- 新增后端域：
  - `backend/app/modules/equipment/*`
  - `backend/app/modules/metrology/*`
  - `backend/app/modules/maintenance/*`
  - `backend/services/equipment/*`
  - `backend/services/metrology/*`
  - `backend/services/maintenance/*`
  - `backend/database/schema/equipment.py`
  - `backend/database/schema/metrology.py`
  - `backend/database/schema/maintenance.py`
- 共享基础设施：
  - `backend/services/notification/event_catalog.py`
  - `backend/services/notification/code_defaults.py`
- 前端新增页面与特性层：
  - `fronted/src/pages/EquipmentLifecycle.js`
  - `fronted/src/pages/MetrologyManagement.js`
  - `fronted/src/pages/MaintenanceManagement.js`
  - `fronted/src/features/equipment/*`
  - `fronted/src/features/metrology/*`
  - `fronted/src/features/maintenance/*`
- 测试：
  - `backend/tests/test_equipment_api_unit.py`
  - `backend/tests/test_metrology_api_unit.py`
  - `backend/tests/test_maintenance_api_unit.py`
  - `fronted/src/pages/EquipmentLifecycle.test.js`
  - `fronted/src/pages/MetrologyManagement.test.js`
  - `fronted/src/pages/MaintenanceManagement.test.js`

## Phase Plan

### P1: 实现 WS05 后端域与提醒/导出基础

- Objective: 落地设备、计量、维护三组表结构、服务、路由和提醒/导出能力，并接入依赖装配与审计。
- Owned paths: `backend/database/schema/equipment.py`; `backend/database/schema/metrology.py`; `backend/database/schema/maintenance.py`; `backend/database/schema/ensure.py`; `backend/services/equipment/*`; `backend/services/metrology/*`; `backend/services/maintenance/*`; `backend/app/modules/equipment/*`; `backend/app/modules/metrology/*`; `backend/app/modules/maintenance/*`; `backend/app/dependency_factory.py`; `backend/app/main.py`; `backend/services/notification/event_catalog.py`; `backend/services/notification/code_defaults.py`; `backend/tests/test_equipment_api_unit.py`; `backend/tests/test_metrology_api_unit.py`; `backend/tests/test_maintenance_api_unit.py`; `backend/tests/test_dependencies_unit.py`
- Dependencies: 现有 SQLite schema ensure 机制可复用；现有通知与审计服务可注入；`WS07` 附件结构按共享契约保存为引用对象。
- Deliverables: 三组新表；三组服务与 API；生命周期状态流转；确认/批准动作；CSV 导出；站内信提醒；后端单元测试。

### P2: 实现 WS05 前端页面与特性层

- Objective: 在不修改路由注册与 capability owner 文件的前提下，交付三张可直接接入的管理页面和其配套 API/状态管理。
- Owned paths: `fronted/src/features/equipment/*`; `fronted/src/features/metrology/*`; `fronted/src/features/maintenance/*`; `fronted/src/pages/EquipmentLifecycle.js`; `fronted/src/pages/MetrologyManagement.js`; `fronted/src/pages/MaintenanceManagement.js`; `fronted/src/pages/EquipmentLifecycle.test.js`; `fronted/src/pages/MetrologyManagement.test.js`; `fronted/src/pages/MaintenanceManagement.test.js`
- Dependencies: P1 的接口契约稳定；现有 `httpClient`、`useAuth`、页面测试栈可复用；`WS02` 路由/权限接入仍由其 own。
- Deliverables: 三张页面；三组前端 API client；表单交互；列表刷新；提醒/导出按钮；页面级测试。

### P3: 完成验证与任务证据归档

- Objective: 运行窄范围后端/前端验证，补 execution/test 工件，并把状态推进到可测试完成态。
- Owned paths: `docs/tasks/docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859/execution-log.md`; `docs/tasks/docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859/test-report.md`; `docs/tasks/docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T173859/task-state.json`
- Dependencies: P1、P2 已交付；本地 `pytest` 与前端 Jest 可运行；任务工件校验脚本可运行。
- Deliverables: 通过的验证命令；执行证据；测试报告；同步后的任务状态。

## Phase Acceptance Criteria

### P1

- P1-AC1: 设备主档支持采购、验收、投用、维护中、计量中、报废等状态流转，且状态变化能写入独立留痕与审计。
- P1-AC2: 计量记录与维护记录支持附件引用、责任人、到期时间、确认/批准动作和导出接口。
- P1-AC3: WS05 能通过现有通知系统发出 `equipment_due_soon`、`metrology_due_soon`、`maintenance_due_soon` 站内信提醒，缺少 recipient 或 channel 时直接失败，不静默跳过。
- P1-AC4: 后端测试覆盖创建、查询、状态流转、提醒派发、导出与审计关键路径。
- Evidence expectation: `execution-log.md` 记录新增表、服务、接口、提醒事件和测试命令；后端测试输出与通知/审计查询结果能证明功能闭环。

### P2

- P2-AC1: 三张页面都能加载各自列表、创建记录，并触发 WS05 对应的状态/确认/批准动作。
- P2-AC2: 页面提供显式的提醒派发和导出入口，并对接口错误给出可见错误提示，不吞错。
- P2-AC3: 页面代码不修改 `routeRegistry.js`、`capabilities.js`、`permission_models.py`，而是以可独立接入的页面模块形式交付给 `WS02`。
- P2-AC4: 页面测试覆盖成功路径、失败提示和关键交互提交，不依赖隐藏上下文。
- Evidence expectation: `execution-log.md` 记录新增前端文件和页面测试命令；Jest 结果能证明页面交互与 API 调用契约一致。

### P3

- P3-AC1: `validate_artifacts.py` 通过，且 `task-state.json` 已同步到可执行/测试后的正确阶段。
- P3-AC2: 后端与前端窄范围命令全部通过，失败项为零。
- P3-AC3: `execution-log.md` 和 `test-report.md` 都记录了每个 acceptance id 的对应证据与剩余风险。
- Evidence expectation: 状态脚本、验证脚本、测试命令与任务工件中的证据引用互相一致。

## Done Definition

本任务完成时必须同时满足：

- P1、P2、P3 全部标记为 `completed`。
- 所有 acceptance ids 都有来自 `execution-log.md` 或 `test-report.md` 的证据。
- 后端新增接口已注册到 FastAPI 应用且依赖装配完成。
- 前端三张页面可独立渲染并通过页面测试。
- 提醒、导出、审计、确认/批准都已落地，不存在“先返回成功、以后补实现”的空路径。
- 对 `WS02` 所拥有的路由和权限接入边界有清晰记录，不以临时兼容方式绕过。

## Blocking Conditions

以下情况必须阻断，而不是引入 fallback：

- 无法在不修改 `WS02` owner 文件的前提下定义本任务的页面与接口边界。
- 现有通知系统无法支持新增事件类型，且用户未允许本任务补齐必要的通知注册代码。
- 调用方无法提供附件引用对象，却仍要求系统伪造附件成功路径。
- 现有测试环境缺失到无法运行后端或前端任一窄范围验证命令。
- 需要通过修改 `backend/app/core/permission_models.py` 或 `fronted/src/routes/routeRegistry.js` 才能宣称 WS05 完成。
