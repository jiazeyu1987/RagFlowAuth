# worker-01 Task

## Goal

落地账号生命周期真实用例，覆盖 `doc/e2e/unit/用户管理.md`、`doc/e2e/unit/修改密码.md`、`doc/e2e/role/01_账号与权限开通.md`、`doc/e2e/role/10_密码重置与账号状态.md`，要求全程走真实后端、真实登录、真实密码变更，不得 mock 或直接改库冒充页面通过。

## Owned Paths

- `fronted/e2e/tests/docs.user-management.spec.js`
- `fronted/e2e/tests/docs.password-change.spec.js`
- `fronted/e2e/helpers/userLifecycleFlow.js`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/pages/ChangePassword.js`
- `fronted/src/features/users/`
- `backend/app/modules/users/`
- `backend/app/modules/auth/`
- `backend/app/modules/me/`
- `backend/tests/test_users*_unit.py`
- `backend/tests/test_auth*_unit.py`
- `doc/e2e/unit/用户管理.md`
- `doc/e2e/unit/修改密码.md`
- `doc/e2e/role/01_账号与权限开通.md`
- `doc/e2e/role/10_密码重置与账号状态.md`

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
- Shared rule: prefer real UI or real API setup within the spec over touching shared bootstrap.
- If you discover a missing real prerequisite that cannot be solved inside owned paths, stop, record the exact prerequisite in `progress.md`, set the worker status to `blocked`, and do not introduce fallback or mock.
- You are not alone in the codebase. Do not revert others' edits. Adapt to concurrent changes.

## Acceptance Criteria

- Add at least one real Playwright spec for user/account lifecycle and one real Playwright spec for password change or reset flow.
- Cover real user creation or update, real enable/disable or reset-password effect, real logout/login verification with old and new passwords where applicable.
- Update the 4 owned docs from “待接入” to “已接入” with actual spec names, real data source, covered/not-covered scope.
- Add or update focused backend tests if you change backend behavior.
- Update `progress.md` at start, first milestone, blocker, and ready-for-validation.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

- 2026-04-05T05:09:59Z Corrective guidance: progress.md has not been refreshed recently. Update progress immediately with your current status. If validation is the next step, use the worker-01 isolated env values in this task doc. If you found a product-side blocker, record it explicitly and mark blocked rather than staying silent.
- 2026-04-05T05:19:37Z Rework guidance: supervisor fixed a real shared-infra bug in `backend/database/tenant_paths.py` that previously mapped different isolated DB files into the same tenant DB root under `data/e2e/tenants/...`. Refresh your workspace and re-run worker-01 isolated validation before keeping the bootstrap/file-lock blocker. Only keep blocked if the failure still reproduces after this fix. If password-change still fails, capture the exact status/body once and avoid repeated invalid login loops that can self-trigger `credentials_locked`.

## Supervisor Notes

- Do not wait for the supervisor to tell you basic file locations; inspect your owned slice and implement end-to-end.
- Prefer one or two reusable slice-specific helpers in `fronted/e2e/helpers/userLifecycleFlow.js` rather than editing shared helpers.
- When you run targeted Playwright locally in this swarm wave, use isolated env values to avoid cross-worker collisions:
  `E2E_FRONTEND_BASE_URL=http://127.0.0.1:33101`
  `E2E_BACKEND_BASE_URL=http://127.0.0.1:38101`
  `E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\worker01_doc_auth.db`
  `E2E_BOOTSTRAP_SUMMARY_PATH=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth\bootstrap-summary-worker01.json`
  `E2E_AUTH_DIR=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth-worker01`
  `E2E_OUTPUT_DIR=D:\ProjectPackage\RagflowAuth\fronted\test-results\worker01`
