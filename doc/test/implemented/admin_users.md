# 管理端 Users（/users）（已实现）

已实现 spec（mock）：
- 创建：`fronted/e2e/tests/admin.users.create.spec.js`
- 创建校验（公司/部门）：`fronted/e2e/tests/admin.users.create.validation.spec.js`
- 列表筛选：`fronted/e2e/tests/admin.users.filters.spec.js`
- 分配权限组：`fronted/e2e/tests/admin.users.assign-groups.spec.js`
- 分配失败提示：`fronted/e2e/tests/admin.users.assign-groups.error.spec.js`
- 删除取消分支：`fronted/e2e/tests/admin.users.delete.cancel.spec.js`
- 列表 API 异常：`fronted/e2e/tests/admin.users.api-errors.spec.js`

已实现 spec（integration）：
- 新增 → 删除：`fronted/e2e/tests/integration.users.create-delete.spec.js`
- 分配权限组：`fronted/e2e/tests/integration.users.assign-groups.spec.js`
- 重置密码（新密码可登录）：`fronted/e2e/tests/integration.users.reset-password.spec.js`

