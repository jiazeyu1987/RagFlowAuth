# WS02 Implementation PRD

- Task ID: `docs-tasks-iso-13485-prd-llm-20260413t162500-dev-20260413T174548`
- Created: `2026-04-13T17:45:48`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于 docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS02-quality-system-hub-and-auth.md 开发 WS02：新增体系文件根入口、子路由前缀预留、工作台壳层与质量域 capability 扩展`

## Goal

在不改动其他质量子域业务实现的前提下，把 `体系文件` 落成一个可访问的前端治理入口，并把质量域 capability/resource/action 模型接入当前认证快照，使 `sub_admin` 不依赖全局管理员权限也能进入 `质量体系` 壳层页面。

## Scope

- 为 `fronted/src/routes/routeRegistry.js` 增加 `质量体系` 根路由与固定子路由前缀预留。
- 为 `fronted/src/components/layout/LayoutSidebar.js` 增加对子路由激活态的支持，确保进入 `/quality-system/*` 时仍高亮根导航。
- 在 `fronted/src/shared/auth/capabilities.js` 冻结质量域资源名与 action 名目录，供前端页面与守卫消费。
- 在 `backend/app/core/permission_models.py` 扩展 auth payload capability snapshot，至少覆盖 `quality_system` 的访问能力，并把 WS02 冻结的质量域资源名写入快照。
- 新增 `fronted/src/pages/QualitySystem.js` 与 `fronted/src/features/qualitySystem/*`，交付根页面壳层、模块卡片、待办容器和子路由占位视图。
- 为上述改动补齐前后端窄范围自动化测试。

## Non-Goals

- 不实现文控、培训、变更、设备、批记录、投诉、CAPA、内审、管理评审等子领域业务表单或业务流程。
- 不改动 `backend/services/compliance/*`、`backend/app/modules/training_compliance/*`、`backend/app/modules/emergency_changes/*`、`backend/app/modules/audit/*`。
- 不创建新的权限存储、权限表字段、独立质量权限系统或兼容 fallback 分支。
- 不把现有训练、审计等旧页面整体迁移到 `/quality-system/*` 真业务路由下；本次只预留固定入口和壳层。
- 不修改 `fronted/`、`docs/maintance/` 等当前真实路径命名。

## Preconditions

- `docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/WS02-quality-system-hub-and-auth.md` 可读。
- `docs/tasks/iso-13485-prd-llm-20260413T162500/development-docs/01-shared-interfaces.md` 可读。
- `docs/tasks/iso-13485-20260413T153016/prd.md` 中质量域 resource/action 表可读。
- 前端测试依赖已安装，可运行 `npm test`。
- 后端测试依赖已安装，可运行 `pytest`。
- Playwright 及浏览器依赖可在当前仓库环境中执行真实浏览器检查。

如果任一项缺失，必须停止并记录到 `task-state.json.blocking_prereqs`，不能用 mock、占位成功或静默降级替代。

## Impacted Areas

- 路由与导航:
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/components/layout/LayoutSidebar.js`
- 认证与 capability:
  - `fronted/src/shared/auth/capabilities.js`
  - `fronted/src/hooks/useAuth.js`
  - `backend/app/core/permission_models.py`
  - `backend/services/auth_me_service.py`
- 新增页面壳层:
  - `fronted/src/pages/QualitySystem.js`
  - `fronted/src/features/qualitySystem/*`
- 相关测试:
  - `fronted/src/routes/routeRegistry.test.js`
  - `fronted/src/components/Layout.test.js`
  - `fronted/src/pages/QualitySystem.test.js`
  - `backend/tests/test_auth_me_service_unit.py`

## Phase Plan

### P1: Deliver quality system hub shell and capability contract

- Objective: 接入 `质量体系` 根入口、固定子路由前缀、壳层页面与质量域 capability 快照扩展，且不侵入其他子工作流业务模块。
- Owned paths: `fronted/src/routes/routeRegistry.js`; `fronted/src/components/layout/LayoutSidebar.js`; `fronted/src/shared/auth/capabilities.js`; `fronted/src/pages/QualitySystem.js`; `fronted/src/features/qualitySystem/*`; `backend/app/core/permission_models.py`; `fronted/src/routes/routeRegistry.test.js`; `fronted/src/components/Layout.test.js`; `fronted/src/pages/QualitySystem.test.js`; `backend/tests/test_auth_me_service_unit.py`
- Dependencies: WS02 development doc and shared interface doc remain authoritative; existing auth payload continues to come from `backend/services/auth_me_service.py` via `snapshot.capabilities_dict()`; existing frontend routing continues to use flat `APP_ROUTES`
- Deliverables: `/quality-system` 根入口和固定子路由前缀预留; `质量体系` 壳层页，包含模块卡片、选中模块态和待办容器; 前后端一致的质量域 capability/resource/action 目录; 自动化测试覆盖关键路由、守卫和 auth payload

## Phase Acceptance Criteria

### P1

- P1-AC1: `routeRegistry.js` 注册 `/quality-system` 根路由和以下固定子路由前缀：`/quality-system/doc-control`、`/quality-system/training`、`/quality-system/change-control`、`/quality-system/equipment`、`/quality-system/batch-records`、`/quality-system/audit`、`/quality-system/governance-closure`；左侧导航出现 `体系文件`，且进入任一子路由时根导航保持激活。
- P1-AC2: `backend/app/core/permission_models.py` 与 `fronted/src/shared/auth/capabilities.js` 都包含 WS02 冻结的质量域 resource/action 目录；auth payload 至少为 `admin` 和 `sub_admin` 输出 `quality_system.view`，并为 `admin` 输出 `quality_system.manage`，从而让 `sub_admin` 能通过 capability 进入壳层。
- P1-AC3: `QualitySystem` 页面只交付入口壳层，不实现子域业务细节，但必须包含模块卡片、固定子路由上下文、能力说明、显式的“已预留/待接入”状态，以及基于现有站内信接口的待办容器。
- P1-AC4: 自动化测试能证明路由元数据、导航可见性、auth capability snapshot 和 `QualitySystem` 壳层页面行为符合预期，且没有通过角色名硬编码绕过页面守卫。
- Evidence expectation: 评审人仅通过查看产品代码、窄范围测试结果和 `execution-log.md`，即可确认 WS02 已把入口、权限和壳层接入现有系统，同时未越界实现其他子领域业务。

## Done Definition

- `质量体系` 根导航和根页面可在前端进入。
- 所有约定子路由前缀已注册并可落到同一壳层页面，不再需要第二套路由系统承接后续工作流。
- auth payload 和前端 capability 目录都包含质量域资源名，且 `sub_admin` 能进入 `quality_system.view` 路由。
- 前后端窄范围测试通过。
- 真实浏览器验证确认导航、根页和子路由预留页面可访问并符合 WS02 壳层定位。
- `execution-log.md` 和 `test-report.md` 记录了每条 acceptance id 的对应证据。

## Blocking Conditions

- 无法读取 WS02 development doc 或上游 source PRD 的 resource/action 定义。
- 当前 auth payload 无法扩展 capability snapshot，或扩展后会破坏现有认证契约。
- 前端测试或 Playwright 运行前置缺失，导致无法完成要求的真实浏览器验证。
- 实现必须修改 WS02 明确禁止主动修改的业务模块才能成立。
- 需要为不存在的质量子域 action 自行发明上游规范之外的业务语义才能完成实现。
