# 发布与退役 SOP

版本: v1.1  
更新时间: 2026-04-03  
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
- 本 SOP 不引用已删除或未纳入当前闭环的旧退役归档实现与历史测试路径。
- 当前仓库内闭环覆盖“退役记录生成 + 保留期内受控查询/下载/预览 + 管理员导出取证包 + 审计留痕”，不覆盖线下纸质批准和外部介质管理。

## 3. 角色与职责

| 角色 | 职责 |
|---|---|
| 具备审核权限的知识库授权用户 | 发起退役、填写退役原因和保留期、在授权范围内查询退役记录 |
| 已授权业务用户 | 在保留期内按知识库授权查询、预览、下载退役文件 |
| 管理员 | 仅通过审计接口查看退役记录清单和导出退役记录包，不参与业务文件上传、删除或审批替代 |
| QA / 合规 | 维护仓库外残余项，例如纸质批准、介质封存、到期销毁或移交记录 |

## 4. 退役前提

- 文档当前状态必须为 `approved`。
- 请求体必须提供 `retirement_reason`。
- 请求体必须提供未来时间戳 `retention_until_ms`。
- 原始文件必须存在，且可复制到仓库内退役目录。

## 5. 仓库内退役流程

1. 具备审核权限且已获相应知识库授权的用户调用 `POST /api/knowledge/documents/{doc_id}/retire`。
2. `RetiredRecordsService.retire_document` 复制原文件到 `data/retired_documents/...`，生成 `retirement_manifest.json`、`checksums.json` 和 ZIP 记录包。
3. 同一服务将退役元数据回写到文档记录，至少包含：
   - `effective_status=archived`
   - `archived_at_ms`
   - `retention_until_ms`
   - `retired_by`
   - `retirement_reason`
   - `archive_manifest_path`
   - `archive_package_path`
   - `archive_package_sha256`
4. 常规知识库文件入口在文档已退役时必须拒绝直接访问，返回 `document_retired_use_archive_route`，避免绕过退役链路。
5. 业务侧在保留期内通过退役文档接口进行受控查询、预览和下载。
6. 管理员通过审计接口导出退役记录包，用于检查、取证或线下归档。

## 6. 受控访问与导出入口

| 入口 | 用途 | 权限控制 |
|---|---|---|
| `POST /api/knowledge/documents/{doc_id}/retire` | 发起退役 | 必须具备审核权限且具备目标知识库访问权 |
| `GET /api/knowledge/retired-documents` | 查询退役记录 | 必须具备文档预览/下载能力，且仅返回已授权知识库范围内记录 |
| `GET /api/knowledge/retired-documents/{doc_id}/preview` | 预览退役文件 | 保留期内、知识库授权通过 |
| `GET /api/knowledge/retired-documents/{doc_id}/download` | 下载退役文件 | 保留期内、知识库授权通过，仍走受控分发与水印逻辑 |
| `GET /api/audit/retired-records` | 管理员查看退役记录清单 | 仅管理员 |
| `GET /api/audit/retired-records/{doc_id}/package` | 管理员导出退役记录包 | 仅管理员；保留期过期时返回 `410` |

## 7. 退役记录包组成

管理员导出的退役记录包应与当前实现一致，至少包含：

- `README.txt`
- `retirement_manifest.json`
- `checksums.json`
- `documents/<原始文件名>`

## 8. 审计留痕要求

当前仓库内至少保留以下事件：

- `document_retire`
- `retired_document_download`
- `retired_record_package_export`

审计记录应带有文档标识、知识库标识、操作者、原因、保留期、包摘要等上下文，供管理员后续按条件筛选。

## 9. 保留期与残余项说明

- 仓库内当前以 `retention_until_ms` 表达保留截止点；保留期届满后，业务下载和管理员取证包导出均不再放行。
- 仓库内当前不替代法规/质量体系对纸质批准、介质保管、长期可读性抽检、到期销毁或移交签字的要求。
- 上述仓库外活动必须在独立受控体系中留档，不得在本仓库内伪造为“已完成”。
