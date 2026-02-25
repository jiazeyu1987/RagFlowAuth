# 已实现用例映射（重点链路）

## 权限矩阵
- `RBAC-001`：`fronted/e2e/tests/rbac.viewer.permissions-matrix.spec.js`
- `RBAC-003`：`fronted/e2e/tests/rbac.unauthorized.spec.js`

## 上传 / 审批 / 搜索联动
- `FLOW-001`（上传 -> 审批通过 -> 可搜索 -> 日志可见）  
  `fronted/e2e/tests/integration.flow.upload-approve-search-logs.spec.js`
- `FLOW-002`（上传 -> 驳回 -> 不可搜索）  
  `fronted/e2e/tests/integration.flow.upload-reject-search-logs.spec.js`
- `FLOW-003`（删除后不可搜索 + 删除日志）  
  `fronted/e2e/tests/integration.flow.delete-removes-search.spec.js`

## 日志过滤与总数
- `ADMIN-L-001 ~ ADMIN-L-004`：`fronted/e2e/tests/audit.logs.filters-combined.spec.js`

## 修改密码可用性
- `AUTH-004 / AUTH-005`：`fronted/e2e/tests/auth.change-password.spec.js`

## 统一预览回归
- `PREVIEW-001 ~ PREVIEW-004`：`fronted/e2e/tests/unified.preview.modal.spec.js`
