# ISO 13485 体系文件治理实现 PRD

- Task ID: `docs-tasks-iso-13485-20260413t153016-prd-md-iso--20260414T122156`
- Created: `2026-04-14T12:21:56`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `基于 docs/tasks/iso-13485-20260413T153016/prd.md 中识别出的差距，完善当前系统中未满足的 ISO 13485 体系文件治理需求，重点补齐质量权限模型、质量系统前端接线、文控单一受控根迁移与批记录模块实现，并提供可独立复核的测试工件`

## Goal

在当前仓库真实结构上，把 ISO 13485 体系文件治理从“已有局部能力但未形成闭环”推进到“质量域权限可授权、质量系统入口可落地、文控受控根唯一、批记录具备基础业务闭环”的可验证状态。

目标不是补一份新的方案文档，而是让下列能力在现有系统里真正可运行并可复核：

- 质量子管理员不依赖全局 `admin` 权限即可执行被授权的质量域操作。
- `/quality-system` 各子路由接到真实工作区，而不是只落在壳层页面。
- 受控合规文档只使用一个主根目录，并由运行时、校验器、种子数据和测试统一引用。
- `batch_records` 从 capability 声明补齐到可用的后端、前端、审计和电子签名集成。

## Scope

- 后端质量权限模型与鉴权入口：
  - `backend/app/core/permission_models.py`
  - `backend/app/core/authz.py`
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
- 质量域 API 路由与服务：
  - `backend/app/modules/document_control/router.py`
  - `backend/app/modules/training_compliance/router.py`
  - `backend/app/modules/change_control/router.py`
  - `backend/app/modules/equipment/router.py`
  - `backend/app/modules/metrology/router.py`
  - `backend/app/modules/maintenance/router.py`
  - `backend/app/modules/complaints/router.py`
  - `backend/app/modules/capa/router.py`
  - `backend/app/modules/internal_audit/router.py`
  - `backend/app/modules/management_review/router.py`
  - `backend/app/modules/audit/router.py`
- 前端质量系统入口与质量页面接线：
  - `fronted/src/routes/routeRegistry.js`
  - `fronted/src/pages/QualitySystem.js`
  - `fronted/src/features/qualitySystem/*`
  - `fronted/src/pages/DocumentControl.js`
  - `fronted/src/pages/EquipmentLifecycle.js`
  - `fronted/src/pages/MaintenanceManagement.js`
  - `fronted/src/pages/MetrologyManagement.js`
  - `fronted/src/features/governanceClosure/*`
  - `fronted/src/shared/auth/capabilities.js`
  - `fronted/src/components/PermissionGuard.js`
- 文控受控根迁移与合规校验：
  - `backend/services/document_control/compliance_root.py`
  - `backend/services/compliance/*.py`
  - `backend/database/schema/training_compliance.py`
  - `scripts/validate_*_repo_compliance.py`
  - `doc/compliance/*` 与新增 `docs/compliance/*`
- 批记录模块：
  - 新增 `backend/database/schema/*`
  - 新增 `backend/services/*`
  - 新增 `backend/app/modules/*`
  - 新增或扩展 `fronted/src/features/*`
  - 新增或扩展 `fronted/src/pages/*`
- 自动化与人工复核工件：
  - `backend/tests/*`
  - `fronted/src/**/*.test.js`
  - `fronted/e2e/tests/*`

## Non-Goals

- 不重命名当前真实目录名，如 `fronted/` 或 `docs/maintance/`。
- 不顺手重构与本任务无关的登录、用户管理、知识库、工具箱等模块。
- 不为兼容旧路径继续保留双根读写逻辑；如需迁移，目标是收敛到单根，不引入 fallback。
- 不在本任务里补齐 ISO 13485 全部域外需求，例如供应商确认、退役归档、R7 周期复核等与本次差距无直接关系的模块。
- 不引入 mock 数据、占位 API、空白页面或默认成功返回。

## Preconditions

- 本地仓库可读写，且允许在 `docs/tasks/` 下持久化任务工件。
- `python`、`rg`、`npm`、`npx playwright` 可运行；缺失任一工具时必须阻断执行。
- 本地后端测试可访问 `backend/tests` 所需 sqlite fixture。
- 前端依赖已安装，且可运行 React 单测与 Playwright。
- 可启动真实后端与前端本地运行环境，用于质量系统浏览器验证。
- 质量域测试账号或等效 fixture 至少具备以下角色场景：
  - `admin`
  - 带质量能力的 `sub_admin`
  - 仅能执行确认/填写的普通用户
- 当前脏工作树中的非本任务改动不得回滚；如与本任务实现直接冲突，必须先显式记录并停下确认。

## Impacted Areas

- 登录后用户载荷中的 capability 快照直接影响前端菜单、路由守卫、模块按钮与 API 权限判定。
- 质量域 API 目前同时混用 `AdminOnly`、参与人判断、通用 KB 权限，需要统一成质量 capability 校验。
- `QualitySystem` 页面当前只接入 `ChangeControl`、`TrainingAckWorkspace`、`GovernanceClosureWorkspace`，其余质量页面虽已存在但未进入真实路由。
- 文控受控根迁移会同时影响：
  - review package 导出
  - 合规校验器
  - training requirement 种子引用
  - 相关单元测试与校验脚本
- 批记录实现需要复用现有电子签名与审计设施，避免另造签名体系。
- 浏览器验证将覆盖真实质量入口、权限菜单、子路由落点与批记录交互，因此 E2E 工件必须与实现同步维护。

## Phase Plan

### P1: 质量 capability 与 API 鉴权对齐

- Objective: 让质量子管理员能够基于 capability/resource/action 获得真实授权，并把质量域 API 从 `AdminOnly`/通用 KB 权限改成一致的质量 capability 校验。
- Owned paths:
  - `backend/app/core/permission_models.py`
  - `backend/app/core/authz.py`
  - `backend/app/core/permission_resolver.py`
  - `backend/services/auth_me_service.py`
  - `backend/app/modules/document_control/router.py`
  - `backend/app/modules/training_compliance/router.py`
  - `backend/app/modules/change_control/router.py`
  - `backend/app/modules/equipment/router.py`
  - `backend/app/modules/metrology/router.py`
  - `backend/app/modules/maintenance/router.py`
  - `backend/app/modules/complaints/router.py`
  - `backend/app/modules/capa/router.py`
  - `backend/app/modules/internal_audit/router.py`
  - `backend/app/modules/management_review/router.py`
  - `backend/app/modules/audit/router.py`
  - `backend/tests/*quality*`
  - `backend/tests/test_auth_me_service_unit.py`
- Dependencies:
  - 现有 `PermissionSnapshot` 与 `auth/me` 载荷结构保持兼容
  - 各质量域现有 service 行为可复用
- Deliverables:
  - 质量 capability 的授权映射规则
  - 统一的质量 capability 鉴权辅助函数
  - 各质量域路由的 capability 化鉴权
  - 覆盖授权与拒绝路径的后端单测

### P2: 质量系统前端入口与真实页面接线

- Objective: 把 `/quality-system` 从壳层导航补齐为真实工作台，让文控、设备/计量/维保、治理闭环等子模块渲染已有页面或工作区，并由 capability 控制进入与操作。
- Owned paths:
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
  - `fronted/src/**/*.test.js`
- Dependencies:
  - P1 已产出可用 capability 快照
  - 现有质量页面和工作区保持真实路由可挂接
- Deliverables:
  - 质量系统子路由与模块目录的真实接线
  - capability 驱动的前端入口和子模块守卫
  - 页面/Hook/守卫单测

### P3: 文控单一受控根迁移到 `docs/compliance`

- Objective: 把受控合规文档根从 `doc/compliance` 收敛到 `docs/compliance`，并同步运行时、校验器、种子引用和测试，确保仓库内只存在一个受控主根。
- Owned paths:
  - `docs/compliance/*`
  - `backend/services/document_control/compliance_root.py`
  - `backend/services/compliance/*.py`
  - `backend/services/compliance/review_package.py`
  - `backend/database/schema/training_compliance.py`
  - `scripts/validate_*_repo_compliance.py`
  - `backend/tests/test_*compliance*`
  - `backend/tests/test_training_compliance_api_unit.py`
- Dependencies:
  - 当前 `doc/compliance` 文档内容可迁移到新主根
  - 所有运行时引用和测试引用必须同步更新
- Deliverables:
  - `docs/compliance/` 受控主根
  - 运行时、校验器、种子数据统一指向 `docs/compliance`
  - 合规校验与 review package 相关测试更新

### P4: 批记录后端闭环

- Objective: 从零补齐批记录后端域模型、API、审计与电子签名集成，覆盖模板管理、执行实例、步骤填写、签名、复核和导出基础能力。
- Owned paths:
  - `backend/database/schema/*batch*`
  - `backend/services/*batch*`
  - `backend/app/modules/*batch*`
  - `backend/app/main.py`
  - `backend/app/dependencies.py`
  - `backend/tests/test_batch_records_api_unit.py`
  - `backend/tests/test_electronic_signature_unit.py`
  - `backend/tests/test_auth_me_service_unit.py`
- Dependencies:
  - 复用现有电子签名与审计能力
  - P1 capability 模型已支持 `batch_records.*`
- Deliverables:
  - 批记录 schema、service、router
  - 模板/执行/签名/复核/导出 API
  - 审计与签名留痕
  - 针对成功与拒绝路径的单测

### P5: 批记录前端工作区与浏览器验证资产

- Objective: 为批记录提供真实前端工作区并接入 `/quality-system/batch-records`，同时补齐单测与 Playwright 证据路径，形成可独立复核的浏览器验证面。
- Owned paths:
  - `fronted/src/pages/*Batch*`
  - `fronted/src/features/*batch*`
  - `fronted/src/pages/QualitySystem.js`
  - `fronted/src/features/qualitySystem/moduleCatalog.js`
  - `fronted/src/**/*.test.js`
  - `fronted/e2e/tests/docs.quality-system.spec.js`
- Dependencies:
  - P4 后端 API 可用
  - 本地浏览器验证环境可启动
- Deliverables:
  - 批记录前端工作区
  - 质量系统批记录入口与交互
  - 前端单测与 Playwright 用例
  - 浏览器验证工件生成路径

## Phase Acceptance Criteria

### P1

- P1-AC1: `auth/me` 返回的 capability 快照对质量子管理员不再只有 `quality_system.view`，而是能按质量域资源返回真实可执行 action。
- P1-AC2: 文控、变更、设备、计量、维保、投诉、CAPA、内审、管评、质量审计等路由不再依赖 `AdminOnly` 作为唯一授权入口，而是使用显式质量 capability 校验。
- P1-AC3: 非授权用户访问对应质量域接口会得到明确 `403`，授权用户在不具备全局 `admin` 时仍可完成对应域操作。
- P1-AC4: 与质量 capability 相关的后端单测覆盖授权成功、授权拒绝和 `auth/me` 快照输出。
- Evidence expectation:
  - `execution-log.md` 记录 capability 映射与 API 鉴权变更
  - 后端单测输出覆盖 P1-AC1 至 P1-AC4

### P2

- P2-AC1: `/quality-system/doc-control`、`/quality-system/equipment`、`/quality-system/batch-records`、`/quality-system/audit` 等子路由不再只显示预留壳层，而是进入真实页面或工作区。
- P2-AC2: 质量系统导航、模块按钮与子模块访问统一使用 capability 守卫，不绕回角色名硬编码。
- P2-AC3: 现有 `DocumentControl`、`EquipmentLifecycle`、`MaintenanceManagement`、`MetrologyManagement`、`GovernanceClosureWorkspace` 被接入真实路由并具备对应入口测试。
- P2-AC4: 前端单测覆盖子路由落点、守卫可见性与关键模块渲染。
- Evidence expectation:
  - `execution-log.md` 记录前端接线路径
  - 前端 Jest 测试结果覆盖 P2-AC1 至 P2-AC4

### P3

- P3-AC1: 运行时代码、合规校验器、review package、training requirement 种子与相关测试统一引用 `docs/compliance/*`。
- P3-AC2: 仓库内受控主根收敛为 `docs/compliance/`，不存在新的双根运行时兼容逻辑。
- P3-AC3: `validate_fda03_repo_compliance.py`、`validate_gbz02_repo_compliance.py`、`validate_gbz04_repo_compliance.py`、`validate_gbz05_repo_compliance.py` 在迁移后仍可通过。
- P3-AC4: review package 与 training compliance 相关单测对新主根通过。
- Evidence expectation:
  - `execution-log.md` 记录根迁移与引用更新
  - 校验脚本与单测输出覆盖 P3-AC1 至 P3-AC4

### P4

- P4-AC1: 后端存在批记录模板、执行实例、步骤写入、复核与导出基础模型和 API。
- P4-AC2: 批记录签名复用现有电子签名能力，不另建第二套签名体系。
- P4-AC3: 批记录关键动作写入审计日志，且未授权用户无法执行模板管理、签名或复核动作。
- P4-AC4: 后端单测覆盖模板创建、执行填写、签名/复核、导出与拒绝路径。
- Evidence expectation:
  - `execution-log.md` 记录 schema/service/router 变更
  - 后端单测输出覆盖 P4-AC1 至 P4-AC4

### P5

- P5-AC1: `/quality-system/batch-records` 存在真实前端工作区，可完成模板查看、执行记录填写、签名/复核入口与导出触发。
- P5-AC2: 批记录前端入口遵循质量 capability 守卫，并与质量系统模块目录一致。
- P5-AC3: 前端单测覆盖批记录页面渲染、能力守卫与主要交互。
- P5-AC4: Playwright 用例在真实浏览器中验证质量系统入口、批记录工作区与至少一个能力受限场景，并产生截图或等效证据文件。
- Evidence expectation:
  - `execution-log.md` 记录批记录前端与 E2E 变更
  - 前端单测、Playwright 证据覆盖 P5-AC1 至 P5-AC4

## Done Definition

- `prd.md`、`test-plan.md`、`task-state.json`、`execution-log.md`、`test-report.md` 五个工件齐备且结构有效。
- P1 至 P5 全部完成，且每个 acceptance id 都有 `execution-log.md` 或 `test-report.md` 中的证据。
- 质量 capability、质量系统路由、受控主根迁移、批记录后端与前端工作区全部落地到真实代码。
- 后端目标单测、前端目标单测、合规校验脚本、Playwright 目标用例全部通过。
- 独立 tester 在 `blind-first-pass` 下基于 `prd.md`、`test-plan.md` 和真实仓库/运行环境给出 `passed` 结论。
- 完成前通过 `check_completion.py --apply`。

## Blocking Conditions

- 无法提供 `python`、`npm`、`playwright`、`rg` 中任一必需工具。
- 质量域测试账号或等效 fixture 缺失，导致无法验证非 `admin` 授权路径。
- 当前脏工作树中的外部改动与受控根迁移或质量入口改造直接冲突，且无法安全合并。
- 无法在本地启动真实前后端环境进行浏览器验证。
- 为了兼容旧路径而被要求保留双根读写、占位页面、mock API 或默认成功分支。
