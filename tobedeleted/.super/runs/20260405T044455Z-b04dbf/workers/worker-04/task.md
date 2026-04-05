# worker-04 Task

## Goal

落地组织管理与日志审计真实用例，覆盖 `doc/e2e/unit/组织管理.md`、`doc/e2e/unit/日志审计.md`，要求通过真实组织调整、真实导入或重建、真实日志生成与真实分页筛选验证可追溯性。

## Owned Paths

- `fronted/e2e/tests/docs.org-management.spec.js`
- `fronted/e2e/tests/docs.audit-logs.spec.js`
- `fronted/e2e/helpers/orgAuditFlow.js`
- `fronted/src/pages/OrgDirectoryManagement.js`
- `fronted/src/pages/AuditLogs.js`
- `fronted/src/features/orgDirectory/`
- `fronted/src/features/audit/`
- `backend/app/modules/org_directory/`
- `backend/app/modules/audit/`
- `backend/tests/test_org*_unit.py`
- `backend/tests/test_audit*_unit.py`
- `doc/e2e/unit/组织管理.md`
- `doc/e2e/unit/日志审计.md`

## Do Not Modify

- `doc/e2e/manifest.json`
- `doc/e2e/README.md`
- `doc/e2e/unit/README.md`
- `doc/e2e/role/README.md`
- `scripts/check_doc_e2e_docs.py`
- `scripts/run_doc_e2e.py`
- `scripts/bootstrap_doc_test_env.py`
- Any other paths not listed in Owned Paths are out of scope unless the supervisor updates this file.

## Dependencies

- Validation contract: `VALIDATION.md`
- Prefer real file import or real backend-triggered organization changes inside the owned slice. Do not fake audit rows.
- If the page exposes a real import path, use a real fixture file. If import support is missing, record the exact blocker instead of mocking the upload.
- You are not alone in the codebase. Do not revert others' edits. Adapt to concurrent changes.

## Acceptance Criteria

- Add real Playwright coverage for at least one organization operation that generates auditable change plus one audit-log query or pagination assertion.
- Ensure audit validation comes from real business actions, not seeded fake rows inserted by the test outside owned business paths.
- Update the 2 owned docs from “待接入” to “已接入” only when true coverage lands; otherwise document the exact blocker.
- Add or update focused backend tests if backend org/audit behavior changes.
- Update `progress.md` at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- Keep helper changes slice-local in `orgAuditFlow.js`.
- When you run targeted Playwright locally in this swarm wave, use isolated env values to avoid cross-worker collisions:
  `E2E_FRONTEND_BASE_URL=http://127.0.0.1:33104`
  `E2E_BACKEND_BASE_URL=http://127.0.0.1:38104`
  `E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\worker04_doc_auth.db`
  `E2E_BOOTSTRAP_SUMMARY_PATH=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth\bootstrap-summary-worker04.json`
  `E2E_AUTH_DIR=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth-worker04`
  `E2E_OUTPUT_DIR=D:\ProjectPackage\RagflowAuth\fronted\test-results\worker04`
