# Upload（/upload）（已实现）

已实现 spec（mock）：
- 上传页冒烟：`fronted/e2e/tests/smoke.upload.spec.js`
- 无 datasets / 上传失败：`fronted/e2e/tests/upload.api-errors.spec.js`
- 表单校验（未选文件提交 / >16MB）：`fronted/e2e/tests/upload.validation.spec.js`
- datasets 500/超时：`fronted/e2e/tests/upload.validation.spec.js`
- KB 切换后 kb_id 参数正确：`fronted/e2e/tests/upload.validation.spec.js`

已实现 spec（integration）：
- 上传 → 驳回 → records 可见：`fronted/e2e/tests/integration.upload.reject.spec.js`

