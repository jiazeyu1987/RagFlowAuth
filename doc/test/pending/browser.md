# Browser（/browser）（待补齐）

- `GET /api/ragflow/documents` 失败/空列表时的 UI（目前覆盖了 datasets 层）
- `GET /api/ragflow/documents/{doc_id}/status`、`GET /api/ragflow/documents/{doc_id}`：最小 API smoke（校验权限/404）
- PDF 预览（pdf.js 路径）
- DOCX 预览（mammoth 渲染路径）
- XLSX 预览（表格渲染路径）
- 下载/批量下载失败提示
- 删除文档（`DELETE /api/ragflow/documents/{doc_id}`）与确认取消分支、失败提示
- 删除成功后：审计 deletion log 是否写入（`GET /api/knowledge/deletions` 或 `GET /api/ragflow/downloads` 对应 UI 的 records）
