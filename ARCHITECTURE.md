# RagflowAuth 架构总览

## 1. 系统定位

RagflowAuth 不是一个单纯的登录页项目，而是一个围绕知识库、权限、审批、合规和若干专用工具搭建的企业内部工作台。当前仓库的核心形态是：

- 后端：FastAPI 单体服务，入口在 `backend/app/main.py`
- 前端：React CRA 单页应用，入口在 `fronted/src/App.js`
- 持久化：SQLite，主库默认位于 `data/auth.db`
- 外部依赖：RAGFlow、OnlyOffice、SMTP/DingTalk、SMB/NAS、Docker CLI

## 2. 后端分层

### 2.1 运行入口

`backend/app/main.py` 负责做四件关键事情：

- 注册 `RequestIdMiddleware`
- 注册 CORS 和异常处理器
- 通过 `_build_router_registration_specs()` 聚合所有业务 router
- 在 `lifespan` 中初始化依赖、基础数据库路径、多租户依赖缓存和备份 `scheduler`

这意味着后端的真实装配中心不在各业务模块里，而在应用层入口。

### 2.2 依赖装配

`backend/app/dependencies.py` 是服务装配根。它把 SQLite store、manager、第三方连接和多租户能力聚合成 `AppDependencies`，再交给 FastAPI 请求上下文使用。

这里有三个非常重要的边界：

- store 负责直接读写 SQLite
- manager/service 负责业务编排和跨 store 协作
- `get_tenant_dependencies()` 基于 `company_id` 解析 tenant 数据库，避免直接把全局依赖塞给所有请求

### 2.3 核心横切能力

- 认证：`backend/core/security.py` + `backend/app/core/auth.py`
- 授权：`backend/app/core/authz.py` + `backend/app/core/permission_resolver.py`
- 多租户：`backend/database/tenant_paths.py`
- 审计：`audit_events`、下载/删除日志、审批事件
- 通知：站内信、通知渠道、通知投递日志
- 可靠性：`backend/services/data_security_scheduler_v2.py`、备份作业、恢复演练
- 文档预览：knowledge preview、preview gateway、OnlyOffice

## 3. 后端业务模块

按 `backend/app/modules/*` 的当前注册情况，系统主要业务域如下：

| 业务域 | 主要入口 | 说明 |
| --- | --- | --- |
| 认证 | `/api/auth/*` | 登录、刷新、登出、`auth/me`、修改密码 |
| 用户与组织 | `/api/users/*`、`/api/org/*` | 用户、公司、部门、组织树 |
| 权限 | `/api/permission-groups/*` | 权限组、文件夹、KB/Chat/Tool 资源选择 |
| 知识库 | `/api/knowledge/*`、`/api/datasets/*`、`/api/ragflow/*` | 目录树、上传、文档、RAGFlow 数据集与文档 |
| 对话与搜索 | `/api/chats/*`、`/api/search*`、`/api/agents*` | 对话、配置、全库搜索 |
| 审批与通知 | `/api/operation-approvals/*`、`/api/inbox/*`、`/api/admin/notifications/*` | 审批流、待办、站内信、通知渠道 |
| 数据安全 | `/api/admin/data-security/*` | 备份、全量备份、恢复演练、计划配置 |
| 合规扩展 | `/api/electronic-signatures/*`、`/api/emergency-changes/*`、`/api/training-compliance/*`、`/api/supplier-qualifications/*` | 电子签名、紧急变更、培训、供应商资质 |
| 专用工具 | `/api/patent-download/*`、`/api/paper-download/*`、`/api/package-drawing/*`、`/api/drug-admin/*`、`/api/nas/*` | 论文/专利下载、包装图纸、药监导航、NAS 导入 |

## 4. 前端架构角色

前端并不承担授权真相源，而是消费后端快照：

- `fronted/src/App.js` 定义路由壳和页面挂载
- `fronted/src/hooks/useAuth.js` 负责登录态、`auth/me` 快照和前端 `can()` 判断
- `fronted/src/components/PermissionGuard.js` 在路由层拦截未登录/未授权访问
- `fronted/src/components/Layout.js` 负责侧边导航、页面标题、未读站内信计数

也就是说，前端是“权限驱动的展示层”，后端才是“权限决策层”。

## 5. 权限与租户流

### 5.1 登录与会话

1. 前端调用 `/api/auth/login`
2. 登录成功后再调用 `/api/auth/me`
3. `tokenStore` 把 access token、refresh token 和 user 快照放进浏览器本地存储
4. 后续请求经 `fronted/src/shared/http/httpClient.js` 自动带 token，遇到 401 尝试刷新
5. 后端 `backend/app/core/auth.py` 会再次校验 token、session、账号状态和 company 作用域

### 5.2 权限快照

后端 `resolve_permissions()` 产出 `PermissionSnapshot`，核心字段包括：

- `can_upload`
- `can_review`
- `can_download`
- `can_copy`
- `can_delete`
- `can_manage_kb_directory`
- `can_view_kb_config`
- `can_view_tools`
- `accessible_tools`
- KB/Chat 的 scope 与引用集合

前端 `useAuth.can()` 再将这份快照翻译成路由与按钮级判断。

### 5.3 多租户边界

`backend/app/core/auth.py` 会优先从 token 或用户对象里提取 `company_id`，再用 `backend/database/tenant_paths.py` 解析 tenant 库路径。默认布局是：

- 全局主库：`data/auth.db`
- 租户库：`data/tenants/company_<id>/auth.db`

这条链路是当前 `tenant` 隔离的核心边界。

## 6. 持久化模型

当前仓库的数据库不是 ORM 模型驱动，而是显式 SQLite schema 驱动：

- schema 初始化：`backend/database/schema/ensure.py`
- 实体模型：`backend/models/*.py`
- 真实运行表：`data/auth.db`

推荐把 `docs/generated/db-schema.md` 当作人类可读的 schema 导航页，把 schema 源文件当作真实来源。

## 7. 部署拓扑

当前主线部署不是 Nixpacks，而是 Dockerfile + Nginx：

- 后端镜像：`backend/Dockerfile`
- 前端镜像：`fronted/Dockerfile`
- 反向代理：`fronted/nginx.conf`

Nginx 的核心作用是：

- 托管前端静态产物
- 同源反代 `/api/`
- 同源反代 `/health`

## 8. 当前架构观察

- `fronted` 目录名沿用了拼写错误，但已成为事实上的前端根目录，短期内应按现状对待。
- 权限真相源明确在后端，前端只做消费和展示；这是好事。
- 业务域已经很多，但仍保持单体仓库和单体 FastAPI 应用形态，适合用文档先理清边界，而不是急于拆服务。
- 当前工作区没有 `doc/` 目录，但 `VALIDATION.md` 仍引用旧的 `doc/e2e` 校验入口，这说明验证体系与现状存在漂移。

## 9. 推荐阅读顺序

1. [FRONTEND.md](FRONTEND.md)
2. [PRODUCT_SENSE.md](PRODUCT_SENSE.md)
3. [SECURITY.md](SECURITY.md)
4. [RELIABILITY.md](RELIABILITY.md)
5. [docs/generated/db-schema.md](docs/generated/db-schema.md)
