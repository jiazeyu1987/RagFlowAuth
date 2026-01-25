# 后端 API 覆盖面（待补齐）

说明：按后端路由罗列“目前没有对应自动化验证”的端点/分支（优先考虑 UI 关键链路与权限/异常态）。

## Users（/api/users/*）
- `GET /api/users/{user_id}`：缺少用例（建议 mock + integration 各 1）
- `PUT /api/users/{user_id}`：缺少用例（建议 mock：字段校验/保存失败；integration：更新后列表回显）

## Knowledge（/api/knowledge/*）
- `GET /api/knowledge/documents/{doc_id}`：缺少用例（建议 API 级用例校验权限与返回结构）
- `GET /api/knowledge/documents/{doc_id}/download`：缺少用例（成功/失败、文件名 header 解析）
- `GET /api/knowledge/documents/{doc_id}/preview`：缺少成功用例（目前只有失败路径；建议 txt/md 成功渲染 + 403/404）
- `POST /api/knowledge/documents/batch/download`：缺少失败用例（500/超时/空 doc_ids/全部无权限）
- `GET /api/knowledge/deletions`：缺少错误态/权限态用例（500/403/空数据）

## Review（/api/knowledge/documents/*）
- `POST /api/knowledge/documents/{doc_id}/reject`：缺少“普通驳回”主流程（prompt 取消/确认、notes 空/有值、接口失败）

## RAGFlow（/api/ragflow/*）
- `GET /api/ragflow/documents/{doc_id}/status`：缺少用例（建议 API smoke）
- `GET /api/ragflow/documents/{doc_id}`：缺少用例（建议 API smoke）
- `GET /api/ragflow/documents/{doc_id}/preview`：缺少用例（若前端未来改为走该端点）
- `DELETE /api/ragflow/documents/{doc_id}`：缺少用例（确认取消/成功/失败 + deletion log）
- `GET /api/ragflow/downloads`：缺少错误态/权限态用例

## Chat（/api/chats/*）
- `GET /api/chats`：缺少用例（分页/过滤/权限）
- `GET /api/chats/my`：缺少用例（与权限组 chat_scope/ids 的过滤关系）
- `GET /api/chats/{chat_id}`：缺少 403/404 用例
- `GET /api/chats/{chat_id}/sessions`：缺少用例（非 admin 只能看到自己的 sessions）
- `POST /api/chats/{chat_id}/completions`：缺少异常态/断线恢复（SSE 错误 chunk 的 UI 行为）

## Data Security（/api/admin/data-security/*）
- `POST /api/admin/data-security/backup/run` / `run-full`：缺少真实集成验证（触发 → jobs 轮询 → 完成/失败）
- `GET /api/admin/data-security/backup/jobs*`：缺少 404/空列表/权限/失败信息展示

## Me（/api/me/kbs）
- `GET /api/me/kbs`：缺少用例（可做最小 API smoke：admin/viewer 返回结构）

