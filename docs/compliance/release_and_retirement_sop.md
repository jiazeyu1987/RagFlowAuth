# 发布与退役 SOP

版本: v1.1
更新时间: 2026-04-14
适用范围: FDA-03 / GBZ-03
当前发布版本: 2.0.0
仓库外残余项: 纸质退役审批单、线下介质封存/移交记录、保留期届满后的线下处置签字仍需在线下受控体系归档。

## 1. 目的

规范当前仓库内已经落地的“文档退役与记录保留期可访问”流程，确保退役动作、保留期控制、受控访问、审计留痕和管理员导出取证使用同一条实现路径。

## 2. 现行实现边界

- 本 SOP 仅使用以下仓库内实现作为 GBZ-03 证据：
  - `backend/services/compliance/retired_records.py`
  - `backend/app/modules/knowledge/routes/retired.py`
  - `backend/app/modules/audit/router.py`
  - `backend/tests/test_retired_document_access_unit.py`
- 当前仓库内闭环覆盖“退役记录生成 + 保留期内受控查询/下载/预览 + 管理员导出取证包 + 审计留痕”，不覆盖线下纸质批准和外部介质管理。

## 3. 退役前提

- 文档当前状态必须为 `approved`。
- 请求体必须提供 `retirement_reason`。
- 请求体必须提供未来时间戳 `retention_until_ms`。
- 原始文件必须存在，且可复制到仓库内退役目录。

## 4. 仓库内退役流程

1. 具备审核权限且已获相应知识库授权的用户调用 `POST /api/knowledge/documents/{doc_id}/retire`。
2. `RetiredRecordsService.retire_document` 复制原文件到 `data/retired_documents/...`，生成 `retirement_manifest.json`、`checksums.json` 和 ZIP 记录包。
3. 系统将退役元数据回写到文档记录，并保留退役原因、保留截止时间、记录包路径和 `archive_package_sha256`。
4. 常规知识库文件入口在文档已退役时必须拒绝直接访问，返回 `document_retired_use_archive_route`。
5. 业务侧在保留期内通过退役文档接口进行受控查询、预览和下载。
6. 管理员通过 `GET /api/audit/retired-records` 查看退役记录清单，并通过 `GET /api/audit/retired-records/{doc_id}/package` 导出记录包。

## 5. 受控访问与导出入口

| 入口 | 用途 | 权限控制 |
|---|---|---|
| `POST /api/knowledge/documents/{doc_id}/retire` | 发起退役 | 必须具备审核权限且具备目标知识库访问权 |
| `GET /api/knowledge/retired-documents` | 查询退役记录 | 必须具备文档预览/下载能力，且仅返回已授权知识库范围内记录 |
| `GET /api/knowledge/retired-documents/{doc_id}/preview` | 预览退役文件 | 保留期内、知识库授权通过 |
| `GET /api/knowledge/retired-documents/{doc_id}/download` | 下载退役文件 | 保留期内、知识库授权通过 |
| `GET /api/audit/retired-records` | 管理员查看退役记录清单 | 仅管理员 |
| `GET /api/audit/retired-records/{doc_id}/package` | 管理员导出退役记录包 | 仅管理员；保留期过期时返回 `410` |

## 6. 退役记录包组成

- `README.txt`
- `retirement_manifest.json`
- `checksums.json`
- `documents/<原始文件名>`

## 7. 审计留痕要求

- 当前仓库内至少保留 `document_retire`、`retired_record_package_export` 等关键事件。
- `/api/audit/retired-records` 用于审计检索退役记录。

## 8. 边界说明

- 本 SOP 只覆盖仓库内主链路，不替代线下纸质批准、介质封存、长期可读性抽检和到期处置签字。

## 9. WS05 Document-Control Obsolete Flow

- Controlled revisions do not use the old direct `effective -> obsolete` transition as the complete contract.
- The system now requires two explicit document-control actions:
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/initiate`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/approve`
- The initiation request must include `retirement_reason` and a future `retention_until_ms`.
- Approval removes the active Ragflow index entry, creates the retired archive package, and forces standard knowledge routes to return `document_retired_use_archive_route`.
- During retention, controlled access must use:
  - `GET /api/knowledge/retired-documents`
  - `GET /api/knowledge/retired-documents/{doc_id}/preview`
  - `GET /api/knowledge/retired-documents/{doc_id}/download`
- After retention expiry, the system returns `410 document_retention_expired`.
- The repository does not auto-delete archived records. Offline destruction or handoff remains outside the repo-owned scope and may only be recorded through `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/destruction/confirm`.
