# Fullstack Test Report

- Time: 2026-04-02 17:11:21
- Repository: `D:\ProjectPackage\RagflowAuth`
- Overall: **PASS**

## Summary

| Scope | Result | Detail |
|---|---|---|
| Backend | PASS | `python -m unittest discover -s backend/tests -p "test_*.py"` -> `237/237` |
| Frontend Build | PASS | `cd fronted; npm run build` |
| Frontend Acceptance | PASS | `22/22` |

## Commands

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` (cwd: `D:\ProjectPackage\RagflowAuth`)
- Frontend Build: `npm run build` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)
- Frontend Acceptance: `npx playwright test e2e/tests/rbac.unauthorized.spec.js e2e/tests/rbac.viewer.permissions-matrix.spec.js e2e/tests/rbac.uploader.permissions-matrix.spec.js e2e/tests/rbac.reviewer.permissions-matrix.spec.js e2e/tests/audit.logs.filters-combined.spec.js e2e/tests/document.version-history.spec.js e2e/tests/documents.review.approve.spec.js e2e/tests/review.notification.spec.js e2e/tests/review.signature.spec.js e2e/tests/document.watermark.spec.js e2e/tests/company.data-isolation.spec.js e2e/tests/admin.config-change-reason.spec.js e2e/tests/admin.data-security.backup.failure.spec.js e2e/tests/admin.data-security.backup.polling.spec.js e2e/tests/admin.data-security.settings.save.spec.js e2e/tests/admin.data-security.share.validation.spec.js e2e/tests/admin.data-security.validation.spec.js e2e/tests/data-security.advanced-panel.spec.js e2e/tests/admin.data-security.restore-drill.spec.js --workers=1` (cwd: `D:\ProjectPackage\RagflowAuth\fronted`)

## Notes

- 本报告基于已实际执行并通过的命令结果汇总。
- `scripts/run_fullstack_tests.ps1` 生成的 2026-04-02 16:08:18 失败结果因 PowerShell 引号转义问题失真，不作为验收证据。
- 运行过程中存在 `RequestsDependencyWarning` 与 Node `DEP0176` 弃用告警，但均未阻断测试和构建。

## Conclusion

后端全量、前端构建、前端验收套件均已通过，可作为当前合规改造验收证据归档。
