# Documents（/documents）（已实现）

审核（approve tab）— mock：
- 通过流程：`fronted/e2e/tests/documents.review.approve.spec.js`
- 冲突覆盖：use-new（approve-overwrite）：`fronted/e2e/tests/documents.review.conflict.spec.js`
- 冲突分支：keep-old（驳回新文件）：`fronted/e2e/tests/documents.review.conflict.keep-old.spec.js`
- 列表/接口错误态（500/504/空数据/403）：`fronted/e2e/tests/documents.review.api-errors.spec.js`
- 删除文档：`fronted/e2e/tests/documents.review.delete.spec.js`
- 批量下载/全选：`fronted/e2e/tests/documents.review.batch-download.spec.js`
- 预览失败提示：`fronted/e2e/tests/documents.review.preview.error.spec.js`
- diff 不支持类型：`fronted/e2e/tests/documents.review.diff.not-supported.spec.js`

记录（records tab）— mock：
- records 过滤 + tab 切换：`fronted/e2e/tests/documents.audit.filters.spec.js`

冲突链路真实集成（integration）：
- upload(old) → approve(old) → upload(new) → approve-overwrite：`fronted/e2e/tests/integration.documents.conflict.overwrite.spec.js`
- upload(old) → approve(old) → upload(new) → close modal：`fronted/e2e/tests/integration.documents.conflict.cancel.spec.js`

