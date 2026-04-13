# WS02：`体系文件`入口、工作台壳层与权限模型

- Workstream ID: `WS02`
- 推荐 owner：前端主导，全栈配合
- 独立性：高

## 目标

把 `体系文件` 从概念变成可访问的治理中枢入口，统一负责导航、工作台壳层、能力资源名与权限快照扩展，为其他工作流提供一致的接入面。

## 来源需求

- 源 PRD 问题项：`GOV-01`
- 源 PRD 章节：`体系文件`治理中枢方案、质量子管理员权限模型、整改实施路线图 `R2`

## 负责边界

- 新增 `体系文件` 根路由与左侧导航入口。
- 定义质量域能力资源名与 action。
- 质量工作台壳层页面、入口卡片、待办容器和模块跳转位。
- 质量子管理员与质量管理员的访问边界。

## 不负责范围

- 不负责文控、培训、变更、设备、批记录等具体业务流程。
- 不负责通用审计 schema。
- 不负责站内信 payload 设计。

## 代码写入边界

前端 owner：

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/components/layout/LayoutSidebar.js`
- `fronted/src/shared/auth/capabilities.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/pages/*QualitySystem*.js`
- `fronted/src/features/qualitySystem/*`

后端 owner：

- `backend/app/core/permission_models.py`

允许新增：

- `fronted/src/pages/QualitySystem.js`
- `fronted/src/features/qualitySystem/*`

禁止主动修改：

- `backend/services/compliance/*`
- `backend/app/modules/training_compliance/*`
- `backend/app/modules/emergency_changes/*`
- `backend/app/modules/audit/*`

## 共享接口

本工作流拥有：

- `/quality-system` 根路由
- 各子工作流路由前缀注册
- 能力资源名和 action 冻结

本工作流消费：

- `WS01` 到 `WS08` 提供的子路由后缀与卡片元数据
- `WS07` 的审计事件埋点结构

## 依赖关系

- 可与 `WS01` 并行启动。
- 是 `WS03`、`WS04`、`WS05`、`WS06`、`WS08` 的共享入口前置。

## 验收标准

- 左侧导航新增 `体系文件`，且通过现有导航模式接入。
- 能力资源名在前后端快照里一致。
- 质量部子管理员可以访问工作台壳层，而不要求全局管理员权限。
- 其他工作流可以通过固定子路由接入，不需要再改第二套路由系统。

## 交接给 LLM 的规则

1. 只负责入口、权限和壳层，不实现子领域业务细节。
2. 所有资源名、action 名由本工作流统一冻结。
3. 不直接在别的工作流页面里实现业务表单，只提供承载壳层与跳转。
4. 任何新增共享文件，必须在总览文档中声明 owner。
