# Upload（/upload）（待补齐）

- 上传成功后自动跳转 /documents：更严格断言（等待跳转 + pending 列表出现该文件）（建议 mock 与 integration 各 1）
- 文件类型覆盖（pdf/docx/pptx/md）：
  - 前端 accept 限制是否符合预期
  - 后端拒绝/不支持类型时的提示
- KB 选择项使用 `ds.name` 还是 `ds.id`：建议补 1 个用例确保与后端 `kb_id` 解析一致（避免“显示名≠真实 id”导致上传到错误库）
- 上传中状态（uploading=true）按钮禁用/文案变化（可补一个轻量用例）
