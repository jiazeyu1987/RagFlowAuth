# 管理端 数据安全/备份（/data-security）（已实现）

已实现 spec（mock）：
- 字段校验：`fronted/e2e/tests/admin.data-security.validation.spec.js`
- 共享目标必填校验：`fronted/e2e/tests/admin.data-security.share.validation.spec.js`
- 保存设置并回显一致：`fronted/e2e/tests/admin.data-security.settings.save.spec.js`
- 保存设置前必须填写变更原因：`fronted/e2e/tests/admin.config-change-reason.spec.js`
- 触发备份并轮询进度：`fronted/e2e/tests/admin.data-security.backup.polling.spec.js`
- 备份失败详情展示：`fronted/e2e/tests/admin.data-security.backup.failure.spec.js`
- 恢复演练记录展示与结果校验：`fronted/e2e/tests/admin.data-security.restore-drill.spec.js`
关联需求 ID: `R7`, `R8`, `R10`
关联门禁: `T-P2-3`, `T-P4-2`, `T-P5-1`
