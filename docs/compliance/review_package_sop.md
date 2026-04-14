# 审核包导出 SOP

版本: v1.0
更新时间: 2026-04-13

- 使用 `/api/audit/controlled-documents` 核对受控文件登记内容。
- 使用 `/api/audit/review-package` 导出审核包。
- 导出包必须包含 `review_package_manifest.json`、`review_package_checksums.json`、`controlled_documents.json` 和 `controlled_documents.csv`。
- 包内受控文件副本来自 `docs/compliance/` 受控主根。
- 线下签字版批准页与仓库外证据应按残余缺口清单另行归档。
