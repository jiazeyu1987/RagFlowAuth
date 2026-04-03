# 集成用例（integration）（已实现）

说明：此类用例依赖真实后端或外部依赖（例如 RAGFlow datasets 可用），默认回归不跑；其中通知设置回归为 mock 场景，用于补足通知链路的前端证据。

已实现 spec：
- 审批通知设置保存与失败任务重试（mock 回归）：`fronted/e2e/tests/review.notification.spec.js`
- 上传 -> 驳回 -> records：`fronted/e2e/tests/integration.upload.reject.spec.js`
- 文档审核冲突 approve-overwrite：`fronted/e2e/tests/integration.documents.conflict.overwrite.spec.js`
- 文档审核冲突 close/cancel：`fronted/e2e/tests/integration.documents.conflict.cancel.spec.js`
- Browser：审核通过后预览：`fronted/e2e/tests/integration.browser.preview.approved.spec.js`
- Chat：会话增删：`fronted/e2e/tests/integration.chat.sessions.spec.js`
- Users：创建删除：`fronted/e2e/tests/integration.users.create-delete.spec.js`
- Users：分配权限组：`fronted/e2e/tests/integration.users.assign-groups.spec.js`
- Users：重置密码（新密码可登录）：`fronted/e2e/tests/integration.users.reset-password.spec.js`
- 权限组：CRUD：`fronted/e2e/tests/integration.permission-groups.crud.spec.js`
- 权限组：资源接口：`fronted/e2e/tests/integration.permission-groups.resources.spec.js`
- 组织架构：新增审计：`fronted/e2e/tests/integration.org-directory.audit.spec.js`
- 组织架构：编辑删除：`fronted/e2e/tests/integration.org-directory.edit-delete.spec.js`
- 诊断接口：`fronted/e2e/tests/integration.diagnostics.spec.js`

关联需求 ID: `R2`, `R4`, `R5`, `R8`
关联门禁: `T-P2-1`, `T-P2-2`, `T-P5-1`
