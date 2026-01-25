# Dashboard（/）（已实现）

已实现 spec：
- 统计卡片 + 快速操作（admin）：`fronted/e2e/tests/dashboard.stats.spec.js`
- stats 500/空 payload 不崩溃（admin）：`fronted/e2e/tests/dashboard.stats.spec.js`
- viewer 视角：仅显示“浏览文档”，可跳转 `/browser`：`fronted/e2e/tests/dashboard.stats.spec.js`

覆盖点：
- `GET /api/knowledge/stats` 正常/500/空返回
- 不同角色（admin/viewer）下按钮显示/隐藏与跳转

