# Dashboard（/）（待补齐）

- viewer 场景：统计卡片点击跳转（目前只测了“浏览文档”按钮；卡片点击可补）
- stats 超时（非网络层 abort，而是后端长时间无响应）下的 UI（可用 `page.route` 延迟/不返回模拟）
- stats 返回非法结构（类型错误/字段为 null）下的容错

