# 退役与记录保留计划

版本: v1.0  
更新时间: 2026-04-03  
当前发布版本: 2.0.0  
适用范围: GBZ-03  
退役对象范围: 当前仅覆盖已进入知识库、状态为 `approved`、且通过现有 `retired_records` 路径执行退役的单份文档记录。  
保留期映射: 由退役请求中的 `retention_until_ms` 明确指定；法规年限换算与批准依据留在线下质量体系。  
归档包校验: 当前路径在生成退役记录包时写入 `checksums.json`，并在管理员导出时校验 `archive_package_sha256`；长期介质可读性抽检仍为仓库外残余项。  
长期可读性复核周期: 当前仓库内未实现定时复核任务，以按需导出退役记录包和线下周期抽检记录补足。  
仓库外残余项: 纸质退役批准、长期介质可读性抽检记录、保留期届满销毁或移交证明仍在仓库外保管。

## 1. 现行实现路径

GBZ-03 当前只采用以下主链路：

- `backend/services/compliance/retired_records.py`
- `backend/app/modules/knowledge/routes/retired.py`
- `backend/app/modules/audit/router.py`
- `backend/tests/test_retired_document_access_unit.py`

## 2. 归档对象

当前实现以“单份已批准知识库文档的退役记录”为最小归档对象，不新建第二套退役主数据系统。

## 3. 最小保留字段

退役记录至少应包含以下信息：

| 字段 | 说明 |
|---|---|
| `doc_id` | 当前退役文档标识 |
| `logical_doc_id` | 文档逻辑链标识 |
| `version_no` | 当前版本号 |
| `kb_id` / `kb_dataset_id` / `kb_name` | 知识库定位信息 |
| `filename` | 原文件名 |
| `status` | 退役前审批状态 |
| `retired_by` | 退役执行人 |
| `retirement_reason` | 退役原因 |
| `archived_at_ms` | 退役时间 |
| `retention_until_ms` | 保留截止时间 |
| `file_sha256` | 文件摘要 |
| `archive_manifest_path` | manifest 路径 |
| `archive_package_path` | 记录包路径 |
| `archive_package_sha256` | 记录包摘要 |

## 4. 受控访问策略

- 业务侧通过 `GET /api/knowledge/retired-documents` 查询退役记录。
- 业务侧通过 `GET /api/knowledge/retired-documents/{doc_id}/preview` 和 `.../download` 在保留期内访问退役文件。
- 普通知识库下载入口对已退役文档返回 `document_retired_use_archive_route`，避免绕过退役管控。
- 管理员通过 `GET /api/audit/retired-records` 查看清单，通过 `GET /api/audit/retired-records/{doc_id}/package` 导出记录包。
- 保留期已过期时，业务下载与管理员记录包导出均返回 `410`。

## 5. 记录包组成

当前记录包最少包括：

- `README.txt`
- `retirement_manifest.json`
- `checksums.json`
- `documents/<原始文件名>`

## 6. 计划边界

- 当前仓库内计划覆盖“退役记录生成、保留期控制、授权访问、管理员导出、审计留痕”。
- 当前仓库内不覆盖法规年限判定、线下纸质批准、介质保管、到期销毁或移交签字。
- 上述未覆盖事项保持为仓库外残余项，不在本计划中伪造完成状态。
