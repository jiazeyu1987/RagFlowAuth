# Chat（/chat）（待补齐）

- SSE/流式异常：500/断线/超时后的 UI（重试、错误提示、状态清理）
- 权限/401/refresh 失败导致的重登链路（Chat 页面端到端）
- Chats 列表与过滤：
  - `GET /api/chats`：分页/过滤（name/chat_id/orderby/desc），以及权限过滤（非 admin 只能看到 allowed chats）
  - `GET /api/chats/my`：与权限组 chat_scope/chat_ids 的联动
- 会话列表与归属：
  - `GET /api/chats/{chat_id}/sessions`：非 admin 只能看到自己的 sessions（以及 403/404）
- completions：
  - `POST /api/chats/{chat_id}/completions`：后端异常时会回 SSE error chunk（`code=-1`），前端 UI 应可见/可恢复
