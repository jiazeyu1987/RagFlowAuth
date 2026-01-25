# 后端 API 覆盖面（已实现）

说明：本文件按后端路由“点名”当前已有自动化测试覆盖到的 API/链路（包含 UI mock 与 @integration）。

## Auth（/api/auth/*）
- `/api/auth/login`：`fronted/e2e/tests/smoke.auth.spec.js`、多处集成用例的 `uiLogin()`
- `/api/auth/logout`：`fronted/e2e/tests/auth.logout.spec.js`
- `/api/auth/refresh`：`fronted/e2e/tests/auth.refresh-failure.spec.js`
- `/api/auth/me`：多处用例依赖（`fronted/e2e/global-setup.js`、mock auth helper）

## Users（/api/users/*）
- `/api/users`（GET/POST）：`fronted/e2e/tests/admin.users.*.spec.js`、`fronted/e2e/tests/integration.users.create-delete.spec.js`
- `/api/users/{id}/password`：`fronted/e2e/tests/integration.users.reset-password.spec.js`

## Knowledge（/api/knowledge/*）
- `/api/knowledge/stats`：`fronted/e2e/tests/dashboard.stats.spec.js`
- `/api/knowledge/upload`：`fronted/e2e/tests/smoke.upload.spec.js`、`fronted/e2e/tests/upload.*.spec.js`、`fronted/e2e/tests/integration.upload.reject.spec.js`
- `/api/knowledge/documents`（GET pending 等）：`fronted/e2e/tests/documents.review.*.spec.js`
- `/api/knowledge/documents/{id}/approve`：`fronted/e2e/tests/documents.review.approve.spec.js`
- `/api/knowledge/documents/{id}/conflict`：`fronted/e2e/tests/documents.review.conflict*.spec.js`
- `/api/knowledge/documents/{id}/approve-overwrite`：`fronted/e2e/tests/documents.review.conflict.spec.js`、`fronted/e2e/tests/integration.documents.conflict.overwrite.spec.js`
- `/api/knowledge/documents/{id}/reject`：`fronted/e2e/tests/documents.review.conflict.keep-old.spec.js`
- `/api/knowledge/documents/{id}`（DELETE）：`fronted/e2e/tests/documents.review.delete.spec.js`
- `/api/knowledge/documents/{id}/preview`：`fronted/e2e/tests/documents.review.preview.error.spec.js`（失败路径）
- `/api/knowledge/documents/batch/download`：`fronted/e2e/tests/documents.review.batch-download.spec.js`
- `/api/knowledge/deletions`：`fronted/e2e/tests/documents.audit.filters.spec.js`（mock）、`fronted/e2e/tests/integration.audit.downloads-deletions.spec.js`

## RAGFlow（/api/ragflow/*）
- `/api/ragflow/datasets`：未直接由前端使用（前端走 `/api/datasets`），暂无直接用例
- `/api/ragflow/documents`（GET + download + batch/download）：`fronted/e2e/tests/browser.*.spec.js`、`fronted/e2e/tests/integration.browser.preview.approved.spec.js`
- `/api/ragflow/downloads`：`fronted/e2e/tests/documents.audit.filters.spec.js`（mock）、`fronted/e2e/tests/integration.audit.downloads-deletions.spec.js`

## Permission Groups（/api/permission-groups/*）
- CRUD：`fronted/e2e/tests/admin.permission-groups.crud.spec.js`、`fronted/e2e/tests/integration.permission-groups.crud.spec.js`
- resources：`fronted/e2e/tests/admin.permission-groups.resources*.spec.js`、`fronted/e2e/tests/integration.permission-groups.resources.spec.js`

## Org Directory（/api/org/*）
- companies/departments/audit：`fronted/e2e/tests/admin.org-directory.*.spec.js`、`fronted/e2e/tests/integration.org-directory.*.spec.js`

## Data Security（/api/admin/data-security/*）
- settings/save/backup polling（mock）：`fronted/e2e/tests/admin.data-security.*.spec.js`

## Chat（/api/chats/*）
- sessions create/delete（integration）：`fronted/e2e/tests/integration.chat.sessions.spec.js`
- completions streaming（mock）：`fronted/e2e/tests/chat.streaming.spec.js`

## Diagnostics（/api/diagnostics/*）
- permissions/ragflow（integration API smoke）：`fronted/e2e/tests/integration.diagnostics.spec.js`

