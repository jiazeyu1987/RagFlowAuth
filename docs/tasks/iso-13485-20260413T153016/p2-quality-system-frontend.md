# P2：质量系统前端接线工作包

- Parent Task: `iso-13485-20260413T153016`
- Source PRD: `docs/tasks/docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156/prd.md`
- Owner Type: frontend / route / workspace
- Parallelism: 可与 `p3-compliance-root-migration.md`、`p4-batch-records.md` 并行；依赖 `p0-p1-quality-permission-api.md` 提供 capability 合同

## 目标

把 `/quality-system` 从壳层页改成真实治理中枢，让已有页面和工作区进入真实子路由，不再停留在“预留模块”状态。

## Owned Paths

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/pages/QualitySystem.js`
- `fronted/src/features/qualitySystem/moduleCatalog.js`
- `fronted/src/features/qualitySystem/useQualitySystemPage.js`
- `fronted/src/shared/auth/capabilities.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/pages/DocumentControl.js`
- `fronted/src/pages/EquipmentLifecycle.js`
- `fronted/src/pages/MaintenanceManagement.js`
- `fronted/src/pages/MetrologyManagement.js`
- `fronted/src/features/governanceClosure/*`
- 新增或修改的质量系统前端测试

## 不在本工作包内

- 不定义新的 capability 名称；必须消费 P0-P1 冻结后的合同
- 不负责 `doc/compliance` 迁移
- 不负责批记录后端 API

## 现状缺口

- `QualitySystem.js` 仍有明显壳层/预留语义
- 真实接入的模块不足，当前主要只有培训、变更、治理闭环
- 文控、设备/计量/维护、审计入口没有全部落到真实工作区

## 实施要求

### 1. 路由与导航

- 继续使用 `routeRegistry.js` 的 `showInNav` 与现有守卫体系
- 禁止新造第二套路由菜单系统
- `/quality-system` 下模块应能直达真实页面或工作区

### 2. capability 守卫

- 统一使用 `PermissionGuard`、`canWithCapabilities`
- 禁止回退到角色名硬编码

### 3. 页面接线

- 至少补齐以下模块的真实落点：
  - 文控
  - 设备
  - 计量
  - 维护
  - 审计/证据
- 治理闭环模块如果继续保留在同一工作区，也必须受 capability 控制

### 4. 壳层清理

- 移除“预留子路由”“只供壳层进入”这类文案与逻辑
- 如果某模块当前确实没有后端能力，必须直接显示明确缺前提，而不是伪装成已接通

## 对其他 LLM 的依赖

- 从 P0-P1 获取 capability 合同
- 从 P4 获取批记录前端最终接入点；若 P4 尚未完成，保留稳定插槽，但不能伪装成功能完成

## 验收标准

- `/quality-system/doc-control`、`/quality-system/equipment`、`/quality-system/audit` 进入真实页面或工作区
- 质量系统各模块统一由 capability 控制显隐和访问
- 不再出现“预留壳层”主路径
- 前端测试覆盖路由落点、守卫和关键模块渲染

## 建议测试

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand QualitySystem.test.js DocumentControl.test.js EquipmentLifecycle.test.js MaintenanceManagement.test.js MetrologyManagement.test.js PermissionGuard.test.js
```

## 交付物

- 前端路由接线变更
- capability 守卫接线摘要
- 新增/更新测试清单
- 未落地模块的明确阻断说明

## Implementation Status（2026-04-14）

已完成本工作包要求的前端接线与测试覆盖，核心证据与实现落点如下：

- 路由落点与 capability 守卫：
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/features/qualitySystem/moduleCatalog.js`
  - `fronted/src/features/qualitySystem/useQualitySystemPage.js`
  - `fronted/src/pages/QualitySystem.js`
- 真实页面/工作区落地：
  - `/quality-system/doc-control` -> `fronted/src/pages/DocumentControl.js`
  - `/quality-system/equipment` -> `fronted/src/pages/QualitySystemEquipment.js`（并提供 `/quality-system/equipment/metrology`、`/quality-system/equipment/maintenance`）
  - `/quality-system/audit` -> `fronted/src/pages/AuditLogs.js`
  - `/quality-system/training` -> `fronted/src/pages/QualitySystemTraining.js`
  - `/quality-system/governance-closure` -> `fronted/src/pages/QualitySystemGovernanceClosure.js`
  - `/quality-system/batch-records` -> `fronted/src/pages/QualitySystemBatchRecords.js`（明确阻断说明，不伪装已接通）
- 单测（通过）：
  - `fronted/src/pages/QualitySystem.test.js`
  - `fronted/src/routes/routeRegistry.test.js`
  - `fronted/src/pages/DocumentControl.test.js`
  - `fronted/src/pages/EquipmentLifecycle.test.js`
  - `fronted/src/pages/MaintenanceManagement.test.js`
  - `fronted/src/pages/MetrologyManagement.test.js`
  - `fronted/src/components/PermissionGuard.test.js`

对应 spec-driven-delivery 工件证据：`docs/tasks/docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156/execution-log.md#Phase-P2`。
