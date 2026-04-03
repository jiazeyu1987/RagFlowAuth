# 已实现用例映射（重点链路）

## 权限矩阵
- `RBAC-001`：`fronted/e2e/tests/rbac.viewer.permissions-matrix.spec.js`
- `RBAC-003`：`fronted/e2e/tests/rbac.unauthorized.spec.js`

## 上传 / 审批 / 搜索联动
- `FLOW-001`：`fronted/e2e/tests/integration.flow.upload-approve-search-logs.spec.js`
- `FLOW-002`：`fronted/e2e/tests/integration.flow.upload-reject-search-logs.spec.js`
- `FLOW-003`：`fronted/e2e/tests/integration.flow.delete-removes-search.spec.js`

## 日志过滤与总数
- `ADMIN-L-001 ~ ADMIN-L-004`：`fronted/e2e/tests/audit.logs.filters-combined.spec.js`
- `REVIEW-006`：`fronted/e2e/tests/document.version-history.spec.js`

## 修改密码可用性
- `AUTH-004 / AUTH-005`：`fronted/e2e/tests/auth.change-password.spec.js`

## 统一预览回归
- `PREVIEW-001 ~ PREVIEW-004`：`fronted/e2e/tests/unified.preview.modal.spec.js`
- `R3` 预览水印与受控预览：`fronted/e2e/tests/document.watermark.spec.js`

## 合规增强链路
- `R5` 审批通知配置与重试：`fronted/e2e/tests/review.notification.spec.js`
- `R6` 电子签名确认与提交流程：`fronted/e2e/tests/review.signature.spec.js`
- `R7/R8` 配置变更原因与版本历史：`fronted/e2e/tests/admin.config-change-reason.spec.js`, `fronted/e2e/tests/document.version-history.spec.js`
- `R9` 公司维度数据隔离：`fronted/e2e/tests/company.data-isolation.spec.js`
- `R10` 恢复演练：`fronted/e2e/tests/admin.data-security.restore-drill.spec.js`
