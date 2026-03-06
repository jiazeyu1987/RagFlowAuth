# 预览卡顿判因指南

本文用于判定预览慢是由哪一段导致：
- 下载（RAGFlow 拉取）
- 转码/解析（Excel/Office 转预览）
- ONLYOFFICE 接口
- ONLYOFFICE 前端脚本加载

## 1. 前端先拿 `requestId`

打开浏览器控制台，点击查看后，关注：

- `[PreviewTrace][Client] preview:ragflow ... requestId=...`
- `[PreviewTrace][Client] onlyoffice:editor-config ... requestId=...`

`requestId` 对应后端 `X-Request-ID`，可用于串联同一次请求日志。

## 2. 后端查同一个 request_id

在后端日志里搜索该 `request_id`，重点看：

- `preview_gateway_done ... elapsed_ms=...`
- `preview_payload_done ... source_fetch_ms=... transform_ms=... elapsed_ms=...`
- `ragflow_meta_lookup_done ... elapsed_ms=...`
- `ragflow_file_download_done ... elapsed_ms=...`
- `ragflow_download_document_done ... elapsed_ms=...`
- `xlsx_to_sheets_done ... elapsed_ms=...`
- `onlyoffice_editor_config_done ... elapsed_ms=...`
- `onlyoffice_file_served ... elapsed_ms=...`

## 3. 快速判因规则

1. `source_fetch_ms` 明显大，`transform_ms` 小  
原因：下载慢（RAGFlow 接口/网络/超时）

2. `source_fetch_ms` 小，`transform_ms` 明显大  
原因：转码/解析慢（常见 Excel/Office）

3. `onlyoffice_editor_config_done` 慢  
原因：ONLYOFFICE 配置接口慢（后端鉴权或生成配置慢）

4. 前端 `onlyoffice:editor-config` 快，但 `onlyoffice:init:*` 慢或报错  
原因：ONLYOFFICE 脚本加载或服务可达性问题（`ONLYOFFICE_SERVER_URL`）

5. `preview:ragflow` 很慢但只出现 `ragflow_meta_lookup_done` 慢  
原因：元数据查询慢（`/datasets/{id}/documents?id=...`）

6. `preview:ragflow` 很慢且 `ragflow_file_download_done` 慢  
原因：文件下载慢（`/datasets/{id}/documents/{doc_id}`）

## 4. 常用排查命令

按关键字过滤（PowerShell）：

```powershell
Get-Content backend.log | Select-String -Pattern "preview_gateway_done|preview_payload_done|ragflow_meta_lookup_done|ragflow_file_download_done|xlsx_to_sheets_done|onlyoffice_editor_config_done|onlyoffice_file_served"
```

按 request_id 过滤：

```powershell
Get-Content backend.log | Select-String -Pattern "YOUR_REQUEST_ID"
```

