# 前端说明

## 1. 技术栈与启动方式

前端位于 `fronted/`，使用 Create React App：

- 入口：`fronted/src/index.js`
- 路由壳：`fronted/src/App.js`
- 包管理：`fronted/package.json`
- 反向代理开发配置：`fronted/src/setupProxy.js`
- 运行时后端 URL 适配：`fronted/src/config/backend.js`

当前并没有 Redux、MobX 或全局状态框架，主要采用“页面 hook + feature API 模块 + shared 工具”的组织方式。

## 2. 路由壳

`fronted/src/App.js` 的结构很清晰：

- `AuthProvider` 包住整棵应用
- `BrowserRouter` 管理路由
- 页面通过 `lazy()` 分块加载
- 大多数业务页外层都包裹 `PermissionGuard` 和 `Layout`

默认落地页逻辑在 `fronted/src/features/auth/defaultLandingRoute.js`：

- `admin` 默认去 `/logs`
- 其他角色默认去 `/chat`

## 3. 认证与权限

### 3.1 登录态来源

`fronted/src/hooks/useAuth.js` 是前端认证核心，负责：

- 调用 `/api/auth/login`
- 在初始化时读取并刷新 token
- 通过 `/api/auth/me` 获取后端权限快照
- 拉取 `me/kbs` 形成 `accessibleKbs`
- 提供 `can()`、`hasRole()`、`canUpload()` 等便捷判断

### 3.2 本地存储

`fronted/src/shared/auth/tokenStore.js` 目前把以下内容放在浏览器本地存储：

- access token
- refresh token
- user 快照

这使前端实现简单，但也意味着安全模型需要明确接受 localStorage 风险，详见 `SECURITY.md`。

### 3.3 路由守卫

`fronted/src/components/PermissionGuard.js` 做两层保护：

- 未登录直接跳 `/login`
- 有 `allowedRoles` 或 `permission` 限制时，不满足则跳 `/unauthorized`

因此路由权限是“页面级硬门槛”，而不是页面内再到处散落判断。

## 4. 布局与导航

`fronted/src/components/Layout.js` 是整个产品体验的骨架：

- 左侧为权限驱动的导航栏
- 右侧为当前页面标题和内容区
- 在移动端切换成抽屉式侧栏
- 会周期性请求审批待办，更新站内信未读数量

导航不是静态写死的。很多项目是否显示取决于：

- 当前角色
- `useAuth` 暴露的 `canViewKbConfig()`、`canViewTools()`、`canUpload()` 等能力
- 特定 `tool` 目标是否在 `accessible_tools` 白名单里

## 5. 路由分组

当前 `fronted/src/App.js` 可以按职责拆成以下几组：

### 5.1 个人与通用

- `/login`
- `/dashboard`
- `/chat`
- `/agents`
- `/change-password`
- `/inbox`
- `/messages`
- `/unauthorized`

### 5.2 知识库与文档

- `/upload`
- `/browser`
- `/document-history`
- `/kbs`
- `/chat-configs`
- `/search-configs`

### 5.3 管理与配置

- `/users`
- `/permission-groups`
- `/org-directory`
- `/data-security`
- `/notification-settings`
- `/logs`

### 5.4 审批与合规

- `/approvals`
- `/approval-config`
- `/electronic-signatures`
- `/training-compliance`

### 5.5 专用工具

- `/tools`
- `/tools/patent-download`
- `/tools/paper-download`
- `/tools/nas-browser`
- `/tools/drug-admin`
- `/tools/nmpa`
- `/tools/package-drawing`

## 6. 代码组织方式

前端目录的主结构是：

- `fronted/src/pages/*`
  页面层，通常只负责把 hook 或组件挂成页面
- `fronted/src/features/*`
  业务域层，包含 API、hook、组件、工具函数和测试
- `fronted/src/shared/*`
  横向复用能力，例如 HTTP、预览器、通用 hook
- `fronted/src/components/*`
  应用级壳组件，如 `Layout`、`PermissionGuard`

一个典型 feature 的组织方式是：

- `api.js` 负责请求
- `useXxxPage.js` 负责页面状态机
- `components/*` 负责局部渲染
- `*.test.js` 负责单元或组件行为测试

## 7. 关键基础设施

### 7.1 HTTP 层

`fronted/src/shared/http/httpClient.js` 负责：

- 拼接 `authBackendUrl`
- 注入 Authorization header
- 遇到 401 时自动刷新 token
- 刷新失败后清空本地认证并跳回登录页

### 7.2 运行时后端地址

`fronted/src/config/backend.js` 的策略是：

- 开发环境优先走 CRA proxy
- 生产环境默认走同源相对路径
- 如果显式配置 `REACT_APP_AUTH_URL`，则改走绝对地址

### 7.3 预览能力

文档预览相关能力分散在：

- `fronted/src/shared/documents/preview/*`
- `fronted/src/shared/preview/*`

这说明前端不仅是表单应用，也承担了 PDF、Markdown、表格等多类型文档的预览体验。

## 8. 主要 feature 分组

### 8.1 身份与个人资料

- `features/auth`
- `features/me`

### 8.2 知识库与文档

- `features/knowledge`
- `features/documents`
- `features/download`

### 8.3 对话与搜索

- `features/chat`
- `features/agents`

### 8.4 人员、组织与权限

- `features/users`
- `features/permissionGroups`
- `features/orgDirectory`

### 8.5 审批、通知与合规

- `features/operationApproval`
- `features/notification`
- `features/electronicSignature`
- `features/trainingCompliance`
- `features/audit`
- `features/dataSecurity`

### 8.6 行业工具

- `features/patentDownload`
- `features/paperDownload`
- `features/packageDrawing`
- `features/drugAdmin`
- `features/nas`

## 9. 当前前端观察

- `fronted/src/components/Layout.js` 里有大量内联样式，说明当前还没有独立设计系统或组件库。
- `fronted/src/hooks/useAuth.js` 把权限能力封装得很完整，是理解页面授权的第一站。
- `fronted/src/shared/http/httpClient.js` 是所有请求的共同入口，排查登录态和 401 行为时优先看它。
- 目录名 `fronted` 虽然拼写奇怪，但已经被 Dockerfile、脚本和代码普遍引用，不宜随手更名。

## 10. 推荐阅读

- `fronted/src/App.js`
- `fronted/src/components/Layout.js`
- `fronted/src/hooks/useAuth.js`
- `fronted/src/shared/http/httpClient.js`
- `fronted/src/features/knowledge/*`
- `fronted/src/features/operationApproval/*`
