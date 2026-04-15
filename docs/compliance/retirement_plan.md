# 退役与记录保留计划

版本: v1.0
更新时间: 2026-04-14
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

## 2. 受控访问策略

- 业务侧通过 `GET /api/knowledge/retired-documents` 查询退役记录。
- 业务侧通过 `GET /api/knowledge/retired-documents/{doc_id}/preview` 和 `GET /api/knowledge/retired-documents/{doc_id}/download` 在保留期内访问退役文件。
- 普通知识库下载入口对已退役文档返回 `document_retired_use_archive_route`。
- 管理员通过 `GET /api/audit/retired-records` 查看清单，通过 `GET /api/audit/retired-records/{doc_id}/package` 导出记录包。
- 保留期已过期时，业务下载与管理员记录包导出均返回 `410`。

## 3. 记录包组成

- `README.txt`
- `retirement_manifest.json`
- `checksums.json`
- `documents/<原始文件名>`

## 4. 计划边界

- 当前仓库内计划覆盖“退役记录生成、保留期控制、授权访问、管理员导出、审计留痕”。
- 当前仓库内不覆盖法规年限判定、线下纸质批准、介质保管、到期销毁或移交签字。
- 上述未覆盖事项保持为仓库外残余项，不在本计划中伪造完成状态。

## 5. WS05 Alignment Notes

- Document-control obsolete handling now uses an explicit initiation and approval path instead of treating `effective -> obsolete` as a single implicit transition.
- The retention boundary is system-owned only up to archive creation, retention-period access control, expiry blocking, and evidence recording.
- The required document-control endpoints are:
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/initiate`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/approve`
  - `POST /api/quality-system/doc-control/revisions/{controlled_revision_id}/obsolete/destruction/confirm`
- `retention_until_ms` remains mandatory and must be provided explicitly by the caller.
- Archive destruction is still not executed automatically by the repository. The system records offline disposal confirmation only after retention expiry; the actual disposal remains a warehouse-external residual item.
