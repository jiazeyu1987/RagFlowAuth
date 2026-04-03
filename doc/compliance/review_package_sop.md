# 审查包导出 SOP

版本: v1.0  
更新时间: 2026-04-03  
适用条目: FDA-03  
适用接口: `/api/audit/controlled-documents`、`/api/audit/review-package`  
仓库外残余项: 线下签字版批准页、纸质作废回收记录、实际发布批次签核记录仍需在线下受控体系归档

## 1. 目的

规范系统文档的受控登记、现行版本识别、审查包导出和完整性核对，确保检查或审计时可直接从系统导出最小可用的文档闭环证据。

## 2. 受控文档登记规则

- 受控文档以 `doc/compliance/controlled_document_register.md` 为系统登记源。
- 每个条目至少包含:
  - 文档代码
  - 标题
  - 文件路径
  - 版本
  - 状态
  - 生效日期
  - 复核截止日期
  - 批准发布版本
  - 审查包分组
- 文档文件本身必须含 `版本:` 和 `更新时间:` 头信息。

## 3. 现行版判定

- 仅 `状态 = effective/current` 且 `批准发布版本 = 当前系统发布版本` 的文档，允许进入系统导出的审查包。
- `superseded/archived` 条目允许保留在登记表中，但不得作为现行版导出。

## 4. 审查包组成

- `README.txt`
- `controlled_documents.json`
- `controlled_documents.csv`
- `review_package_manifest.json`
- `review_package_checksums.json`
- `documents/` 下的现行受控文档副本

## 5. 操作步骤

1. 管理员先调用 `/api/audit/controlled-documents` 核对当前发布版本下的登记状态。
2. 管理员调用 `/api/audit/review-package` 导出审查包，可附带公司环境信息。
3. 系统在审计日志中记录 `compliance_review_package_export` 事件。
4. 审计员核对 `review_package_manifest.json`、`review_package_checksums.json` 和文档副本。

## 6. 异常处置

- 文档登记缺失、路径缺失、版本头不一致或发布版本不匹配:
  该文档不得进入审查包，需先修复登记表或文件元数据。
- 审查包摘要不一致:
  该包不得作为审查证据，必须重新导出。
- 仓库外签字或纸质回收记录:
  仅能在线下受控体系归档，系统内不得伪造为已闭环。
