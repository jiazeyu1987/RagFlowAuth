# WS06：文控前端工作区接线

- Parent Task: `document-control-flow-parallel-20260414T151500`
- Owner Type: frontend / workflow / workspace
- Parallelism: 依赖 `WS01` 到 `WS05` 的稳定 API；可以先做骨架，但最终接线必须在合同稳定后完成

## 目标

把当前文控页面从“查看修订列表 + 直接改状态按钮”重构成目标流程驱动的工作区，前端只消费稳定合同，不再自己主导流程语义。

## Owned Paths

- `fronted/src/pages/DocumentControl.js`
- `fronted/src/features/documentControl/`
- `fronted/src/pages/DocumentControl.test.js`
- `fronted/src/features/documentControl/useDocumentControlPage.test.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`

## Shared Integration Paths

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/features/qualitySystem/moduleCatalog.js`
- `fronted/src/components/PermissionGuard.js`

## 不在本包内

- 后端审批矩阵和加签规则
- 培训后端门禁计算
- 发布台账写入
- 部门确认后端数据模型
- 作废/销毁后端调度逻辑

## 当前差距

- 当前页面直接暴露 `Move to in_review / approved / effective / obsolete`。
- 页面没有审批步骤、驳回原因、培训门禁、发布台账、部门确认、留存信息视图。
- 页面默认把当前后端状态机当成唯一流程。

## 实施要求

### 1. 去掉直接状态按钮

- 不再允许用户直接点击把修订改成 `approved`、`effective`、`obsolete`。
- 所有动作必须映射到后端的显式业务动作，例如：
  - 提交流程
  - 审批/驳回
  - 重提
  - 发布
  - 生成培训
  - 查看部门确认
  - 发起作废

### 2. 工作区结构

- 至少展示：
  - 当前审批步骤和待处理人
  - 驳回原因和历史动作
  - 培训门禁状态
  - 发布记录和被替代版本
  - 部门确认状态
  - 作废 / 留存信息

### 3. 阻断提示

- 后端未满足前提时，前端必须显示明确阻断原因。
- 不允许把“接口还没接好”伪装成流程成功或假按钮。

### 4. 权限与可见性

- 页面动作和模块展示必须继续复用现有 capability / `PermissionGuard`。
- 不允许重新按角色名硬编码权限。

## 验收标准

- 文控页面不再显示直接状态跳转按钮。
- 页面能消费审批、培训、发布、部门确认、作废/留存这几类后端合同。
- 阻断状态有明确提示，不伪造完成。
- 相关前端测试覆盖关键工作区交互和错误状态。

## 建议测试

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js PermissionGuard.test.js
```

重点补测：

- 审批中、驳回后、待培训、待发布、待部门确认、已作废 6 类视图
- 各业务动作按钮的显隐和禁用
- 后端返回阻断错误时的用户可读提示

## 交付物

- 文控工作区页面重构说明
- 新旧交互映射表
- 通过的前端测试清单
