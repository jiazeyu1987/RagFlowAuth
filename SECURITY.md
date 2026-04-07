# 安全说明

## 1. 身份与会话模型

当前后端使用 `JWT` + 会话校验的组合，而不是纯无状态 token：

- `backend/core/security.py` 配置 AuthX
- `backend/app/core/auth.py` 负责 access token 解析、session 校验和账号状态检查
- `backend/services/auth_session*` 管理登录 session

AuthX 当前允许 token 来自：

- headers
- cookies
- query string

这提高了兼容性，但也意味着安全审查要更严格。

## 2. 登录态在前端的落点

前端 `fronted/src/shared/auth/tokenStore.js` 把 access token、refresh token 和 user 快照放进 localStorage。当前安全结论必须如实写成：

- 这是现状，不是最佳实践
- 它依赖前端环境不存在恶意脚本注入
- 任何长期安全加固方案都应优先评估这里

## 3. 后端授权边界

权限不是散落在页面上的字符串，而是后端统一生成的快照：

- `backend/app/core/permission_resolver.py` 生成 `PermissionSnapshot`
- `backend/services/auth_me_service.py` 把快照序列化到 `/api/auth/me`
- 前端 `useAuth.can()` 再将其转成 UI 判断

关键资源包括：

- KB 文档
- RAGFlow 文档
- KB 目录
- KB 配置
- tools

## 4. tenant 边界

`tenant` 隔离是当前安全设计中的关键一层：

- `backend/app/core/auth.py` 会从 payload 或 user 提取 `company_id`
- `backend/database/tenant_paths.py` 决定 tenant DB 路径
- 未命中 company 作用域时才会回退到全局依赖

因此，tenant 作用域错误比一般业务 bug 更高风险。

## 5. 密码与账号控制

用户表和相关逻辑已经包含以下控制项：

- 密码历史
- 最近密码重复检查
- 登录失败计数
- 锁定窗口
- 最大登录 session 数
- idle timeout
- 是否允许修改密码
- 定时禁登

这些控制分别落在：

- `users` 表
- `password_history` 表
- `backend/services/users/store.py`
- `/api/auth/password`

## 6. ONLYOFFICE 相关配置

当前 `.env` 和 `backend/app/core/config.py` 暴露了 `ONLYOFFICE` 配置项：

- `ONLYOFFICE_ENABLED`
- `ONLYOFFICE_SERVER_URL`
- `ONLYOFFICE_JWT_SECRET`
- `ONLYOFFICE_PUBLIC_API_BASE_URL`
- `ONLYOFFICE_FILE_TOKEN_TTL_SECONDS`
- `ONLYOFFICE_FILE_TOKEN_SECRET`

这说明 OnlyOffice 不是假设项，而是已经进入代码约束的外部集成。部署前必须确认这些值，而不是默认沿用示例值。

## 7. 当前安全警示项

### 7.1 默认 JWT secret

`backend/app/core/config.py` 中的默认 `JWT_SECRET_KEY` 仍是示例值。生产环境如果不覆盖，就是高风险配置。

### 7.2 localStorage token

浏览器端 token 存储在 localStorage，意味着：

- XSS 风险直接影响 token
- 前端依赖严格的脚本来源控制

### 7.3 多来源 token

AuthX 接受 headers、cookies、query string 三种 token 位置。对于某些部署环境，这会放大误传或日志泄露风险。

### 7.4 CORS 与同源依赖

当前设计明显偏好同源代理。若改成跨域部署，必须同步审查：

- `CORS_ORIGINS`
- `REACT_APP_AUTH_URL`
- `fronted/src/config/backend.js`
- `fronted/src/setupProxy.js`

## 8. 部署前安全检查单

- 覆盖默认 JWT secret
- 审查 OnlyOffice secret 和公开 API 地址
- 审查 SMTP、DingTalk 等通知凭据是否通过安全方式注入
- 审查是否真的需要 query string token
- 审查浏览器端是否接受 localStorage token 风险
- 审查 tenant 数据库路径是否符合实际组织边界

## 9. 当前结论

这个仓库的授权结构是清楚的，权限真相源也比较集中；真正需要持续警惕的是默认配置、token 存储方式和 tenant 边界。
