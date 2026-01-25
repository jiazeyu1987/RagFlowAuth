# Documents（/documents）（待补齐）

审核（approve tab）：
- “驳回”主流程（非冲突 reject）：prompt 取消/确认、notes 为空/有值、接口失败提示
- `GET /api/knowledge/documents/{doc_id}`：最小 API smoke（404/权限/返回结构）
- 下载单个文档成功/失败（含 Content-Disposition 文件名解析）
- 批量下载失败（500/超时）提示
- diff 成功路径（md/txt），以及“文件过大”报错路径（>2500 行）

记录（records tab）：
- 403/500/空数据：UI 反馈与可操作性（目前 records 只覆盖了过滤与 tab）
