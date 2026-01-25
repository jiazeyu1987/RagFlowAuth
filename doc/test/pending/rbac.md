# RBAC（待补齐）

viewer 访问以下 admin-only 页面应跳转 `/unauthorized`：
- `/permission-groups`
- `/org-directory`
- `/data-security`

以及 viewer 对“审核/上传/删除”等能力点的菜单显隐与路由保护（按 PermissionGuard + useAuth.can 的矩阵补齐）。

