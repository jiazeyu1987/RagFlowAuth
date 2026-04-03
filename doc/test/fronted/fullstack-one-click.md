# 一键前后端测试

## 命令
- PowerShell：`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_fullstack_tests.ps1"`
- 批处理（双击可用）：`.\scripts\run_fullstack_tests.bat`

## 默认执行内容
- 后端：`python -m unittest discover -s backend/tests -p "test_*.py"`
- 前端构建：`cd fronted && npm run build`
- 前端合规验收：`cd fronted && npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/rbac.viewer.permissions-matrix.spec.js e2e/tests/rbac.uploader.permissions-matrix.spec.js e2e/tests/rbac.reviewer.permissions-matrix.spec.js e2e/tests/audit.logs.filters-combined.spec.js e2e/tests/document.version-history.spec.js e2e/tests/documents.review.approve.spec.js e2e/tests/review.notification.spec.js e2e/tests/review.signature.spec.js e2e/tests/document.watermark.spec.js e2e/tests/company.data-isolation.spec.js e2e/tests/admin.config-change-reason.spec.js e2e/tests/admin.data-security.backup.failure.spec.js e2e/tests/admin.data-security.backup.polling.spec.js e2e/tests/admin.data-security.settings.save.spec.js e2e/tests/admin.data-security.share.validation.spec.js e2e/tests/admin.data-security.validation.spec.js e2e/tests/data-security.advanced-panel.spec.js e2e/tests/admin.data-security.restore-drill.spec.js --workers=1`

## 说明
- 此脚本默认生成“后端全量 + 前端构建 + 前端合规验收”的组合报告，不等同于 `npm run e2e:all` 全量 Playwright 回归。
- 如果需要前端全量回归，单独执行：`cd fronted && npm run e2e:all`
- 自定义命令优先使用不含嵌套引号的形式；如果必须使用嵌套引号，建议写入单独的 `.ps1`/`.cmd` 包装脚本后再调用。

## 报告输出
- 时间戳报告：`doc/test/reports/fullstack_test_report_YYYYMMDD_HHMMSS.md`
- 最新报告（覆盖）：`doc/test/reports/fullstack_test_report_latest.md`
- 合规验收归档以 `fullstack_test_report_latest.md` 和最近一次真实 PASS 的时间戳报告为准；调试产物、失真 FAIL 报告和旧口径报告不得作为验收证据。
- 目录索引说明：`doc/test/reports/README.md`

## 可选参数
- 自定义后端命令：
  `.\scripts\run_fullstack_tests.ps1 -BackendCommand "python -m unittest backend.tests.test_document_versioning_unit -v"`
- 自定义前端构建命令：
  `.\scripts\run_fullstack_tests.ps1 -FrontendBuildCommand "npm run build"`
- 自定义前端验收命令：
  `.\scripts\run_fullstack_tests.ps1 -FrontendCommand "npx playwright test e2e/tests/document.version-history.spec.js --workers=1"`
- 自定义报告文件：
  `.\scripts\run_fullstack_tests.ps1 -OutputFile "doc/test/reports/my_report.md"`
