# Frontend Playwright 测试总览

## 目标
- 提供一套可一键执行的 Playwright 自动化测试。
- 覆盖主要页签与关键业务链路（上传/审批/搜索/对话/权限/日志）。
- 产出可回放的失败证据（trace/screenshot/video）与 HTML 报告。

## 范围
- 前端：`fronted/src` 主要页面与交互流程。
- 后端联动：`backend` API（mock 与 integration 两层）。
- 自动化入口：`fronted/playwright.config.js`、`fronted/e2e/tests/**`。

## 分层
- `@smoke`：快速冒烟，提交前必跑。
- `@regression`：常规回归，覆盖主路径与权限分支。
- `@integration`：真实后端联调，验证上传-审批-搜索-日志全链路。

## 一键执行
- 全量（含 integration）：`cd fronted && npm run e2e:all`
- 合规验收套件：`cd fronted && npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/rbac.viewer.permissions-matrix.spec.js e2e/tests/rbac.uploader.permissions-matrix.spec.js e2e/tests/rbac.reviewer.permissions-matrix.spec.js e2e/tests/audit.logs.filters-combined.spec.js e2e/tests/document.version-history.spec.js e2e/tests/documents.review.approve.spec.js e2e/tests/review.notification.spec.js e2e/tests/review.signature.spec.js e2e/tests/document.watermark.spec.js e2e/tests/company.data-isolation.spec.js e2e/tests/admin.config-change-reason.spec.js e2e/tests/admin.data-security.backup.failure.spec.js e2e/tests/admin.data-security.backup.polling.spec.js e2e/tests/admin.data-security.settings.save.spec.js e2e/tests/admin.data-security.share.validation.spec.js e2e/tests/admin.data-security.validation.spec.js e2e/tests/data-security.advanced-panel.spec.js e2e/tests/admin.data-security.restore-drill.spec.js --workers=1`
- 回归（不含 integration）：`cd fronted && npm run e2e`
- 冒烟：`cd fronted && npm run e2e:smoke`
- 联调：`cd fronted && npm run e2e:integration`
- 报告：`cd fronted && npm run e2e:report`
- 组合报告：`powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_fullstack_tests.ps1"`

## 文档索引
- 测试项清单：`doc/test/fronted/test-items.md`
- 测试方案：`doc/test/fronted/test-strategy.md`
- 报告格式：`doc/test/fronted/report-format.md`
- 已实现映射：`doc/test/fronted/implemented-mapping.md`
