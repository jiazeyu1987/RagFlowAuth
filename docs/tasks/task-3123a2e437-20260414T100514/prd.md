# 前端用户可见文案规范化 PRD

- Task ID: `task-3123a2e437-20260414T100514`
- Created: `2026-04-14T10:05:14`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `解决当前前端里的乱码问题、英文不是中文的问题、描述不正式的问题`

## Goal

将当前前端里用户可直接看到的英文、半成品描述和不正式提示统一为正式中文。

本任务只处理“当前前端真实可见”的文案，不做全仓中文化，不改接口契约、路由结构、权限结构、`data-testid` 或内部标识。

## Scope

- `fronted/src/pages/Tools.js`
- `fronted/src/App.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/pages/KnowledgeUpload.js`
- `fronted/src/shared/documents/preview/OnlyOfficeViewer.js`
- `fronted/src/pages/Unauthorized.js`
- `fronted/src/pages/ChangeControl.js`
- `fronted/src/pages/QualitySystem.js`
- `fronted/src/features/governanceClosure/GovernanceClosureWorkspace.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`
- 以上路径直接渲染到用户界面的标题、说明、按钮、分页、空态、加载态、错误态、成功态、确认提示和分页提示文案

## Non-Goals

- 不做全仓英文清理，只处理当前路由树和共享壳层里真实会出现在浏览器里的文案
- 不修改未接入当前路由树、当前用户无法直接到达的页面，仅因为文件存在就纳入范围
- 不修改后端 API、请求/响应字段、数据库、日志、变量名、组件名或路由 path
- 不引入 fallback、mock、silent downgrade 或兼容分支
- 不把领域缩写当成乱码处理；像 `CAPA`、`WS04`、`WS08`、`NMPA`、`user_id` 这类标识只在实际出现在用户文案中时再判断是否保留

## Preconditions

- `fronted/` 依赖已安装，`npm` 可用
- `Python` 可用，仓库现有 Playwright 配置可以启动前端和后端测试服务
- Playwright 浏览器二进制已安装，能够运行 `chromium` 项目
- 现有认证夹具可用，至少要能访问 `viewer`、`admin` 等用于浏览器验证的角色
- 如果浏览器、前端或后端不可用，必须直接停止并报告缺失前提，不能靠产品侧降级掩盖问题

## Impacted Areas

- `fronted/src/App.js`
- `fronted/src/components/PermissionGuard.js`
- `fronted/src/components/Layout.js`
- `fronted/src/pages/Tools.js`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/pages/KnowledgeUpload.js`
- `fronted/src/pages/Unauthorized.js`
- `fronted/src/pages/ChangeControl.js`
- `fronted/src/pages/QualitySystem.js`
- `fronted/src/features/governanceClosure/GovernanceClosureWorkspace.js`
- `fronted/src/shared/documents/preview/OnlyOfficeViewer.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`
- `fronted/e2e/tests/tools.navigation.spec.js`
- `fronted/e2e/tests/rbac.unauthorized.spec.js`
- `fronted/e2e/tests/routes.direct-pages.spec.js`

## Phase Plan

### P1: 统一全局壳层与共享加载/错误文案

- Objective: 将全局 Suspense / 权限守卫 / 用户管理 / 上传页 / OnlyOffice 预览中用户可见的英文 loading、error、empty copy 统一为正式中文。
- Owned paths:
  - `fronted/src/App.js`
  - `fronted/src/components/PermissionGuard.js`
  - `fronted/src/pages/UserManagement.js`
  - `fronted/src/pages/KnowledgeUpload.js`
  - `fronted/src/shared/documents/preview/OnlyOfficeViewer.js`
- Dependencies:
  - 路由与权限逻辑保持不变
  - 现有页面组件继续由当前路由树接入
- Deliverables:
  - `App` 和 `PermissionGuard` 的加载态中文化
  - `UserManagement` 的加载/错误态中文化
  - `KnowledgeUpload` 中与当前用户可见有关的英文提示中文化
  - `OnlyOfficeViewer` 的错误提示中文化

### P2: 统一 Tools 页面用户可见文案

- Objective: 将 `Tools` 页面中用户可见的英文描述、分页、空态和操作提示统一为正式中文。
- Owned paths:
  - `fronted/src/pages/Tools.js`
- Dependencies:
  - `useToolsPage` 的分页与打开逻辑保持不变
  - 仍然允许外部工具名称或系统名保留必要的专有名词
- Deliverables:
  - 页面标题、卡片描述、分页文案、空态与错误态中文化
  - 维持当前分页/跳转/弹窗行为

### P3: 统一既有业务页与共享用户错误映射文案

- Objective: 将 `/unauthorized`、质量体系壳层、WS04、WS08 以及共享错误映射中的用户可见英文统一为正式中文。
- Owned paths:
  - `fronted/src/pages/Unauthorized.js`
  - `fronted/src/pages/ChangeControl.js`
  - `fronted/src/pages/QualitySystem.js`
  - `fronted/src/features/governanceClosure/GovernanceClosureWorkspace.js`
  - `fronted/src/shared/errors/userFacingErrorMessages.js`
- Dependencies:
  - P1、P2 完成后继续沿用当前路由树
  - `routeRegistry` 与 `Layout` 的现有接入不变
- Deliverables:
  - `/unauthorized` 页面正式中文化
  - `/quality-system` 壳层与 WS04、WS08 页面正式中文化
  - 共享错误码与前缀映射返回正式中文，不再回落到英文默认提示

## Phase Acceptance Criteria

### P1

- P1-AC1: `App` 与 `PermissionGuard` 的加载态对用户显示正式中文，不再出现 `Loading...` 这类英文壳层文案。
- P1-AC2: `UserManagement`、`KnowledgeUpload` 与 `OnlyOfficeViewer` 的用户可见错误/加载/空态文案为正式中文。
- Evidence expectation: 对应单元测试通过，real-browser 验证能看到这些中文文案并留有截图、trace 或视频证据。

### P2

- P2-AC1: `/tools` 页面上的标题、描述、分页、空态与错误提示均为正式中文，用户仍可看到必要的专有名词，但不再看到英文自然语言描述。
- P2-AC2: `/tools` 页面的分页切换、空态与工具打开行为保持不变。
- Evidence expectation: 单元测试与 Playwright real-browser 测试都覆盖 `Tools` 页面中文文案和分页可见性。

### P3

- P3-AC1: `/unauthorized`、`/quality-system`、`/quality-system/change-control`、`/quality-system/governance-closure` 的用户可见文案为正式中文。
- P3-AC2: `mapUserFacingErrorMessage` 对已知错误码与前缀返回正式中文，不再输出英文默认提示。
- Evidence expectation: 单元测试覆盖共享错误映射，real-browser 覆盖上述路由并保存可回溯证据文件。

## Done Definition

- 所有阶段完成，所有稳定 acceptance id 均在执行日志或测试报告里有对应证据
- 当前前端真实可见的英文/不正式文案热点已按范围收敛到正式中文
- real-browser 验证通过并留下可追溯证据
- 不依赖 fallback、mock 或 silent downgrade 来伪造成功

## Blocking Conditions

- Playwright 浏览器、前端启动或后端启动失败
- 认证夹具缺失或无法进入目标路由
- 目标页面必须靠 fallback、mock 或静默降级才能通过
- 发现当前工作树里已有未关联的修改与本任务直接冲突，且无法在不覆盖他人改动的前提下继续
