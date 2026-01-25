# Auth / Shell / RBAC（已实现）

已实现 spec：
- 登录冒烟：`fronted/e2e/tests/smoke.auth.spec.js`
- Layout/菜单与基础导航：`fronted/e2e/tests/smoke.shell.spec.js`
- 路由可达性：`fronted/e2e/tests/smoke.routes.spec.js`
- 登出（UI + 本地状态清理）：`fronted/e2e/tests/auth.logout.spec.js`
- refresh 失败自动重登（本地状态清理）：`fronted/e2e/tests/auth.refresh-failure.spec.js`
- RBAC：viewer 访问 `/users` 被拦截：`fronted/e2e/tests/rbac.unauthorized.spec.js`

