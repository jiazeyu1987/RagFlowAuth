# worker-02 Task

## Goal

落地权限分组与菜单生效真实用例，覆盖 `doc/e2e/unit/权限分组.md`、`doc/e2e/role/02_权限组与菜单生效.md`，要求通过真实权限组创建/编辑、真实用户重新登录、真实菜单与页面访问结果验证权限生效。

## Owned Paths

- `fronted/e2e/tests/docs.permission-groups.spec.js`
- `fronted/e2e/tests/docs.role.permission-menu.spec.js`
- `fronted/e2e/helpers/permissionGroupsFlow.js`
- `fronted/src/pages/PermissionGroupManagement.js`
- `fronted/src/features/permissionGroups/`
- `backend/app/modules/permission_groups/`
- `backend/app/modules/user_kb_permissions/`
- `backend/app/modules/user_chat_permissions/`
- `backend/tests/test_permission*_unit.py`
- `doc/e2e/unit/权限分组.md`
- `doc/e2e/role/02_权限组与菜单生效.md`

## Do Not Modify

- `doc/e2e/manifest.json`
- `doc/e2e/README.md`
- `doc/e2e/unit/README.md`
- `doc/e2e/role/README.md`
- `scripts/check_doc_e2e_docs.py`
- `scripts/run_doc_e2e.py`
- `scripts/bootstrap_doc_test_env.py`
- `fronted/src/pages/UserManagement.js`
- `fronted/src/pages/Chat.js`
- Any other paths not listed in Owned Paths are out of scope unless the supervisor updates this file.

## Dependencies

- Validation contract: `VALIDATION.md`
- Use real permission group data, real user binding, real logout/login, real menu and route observations.
- Avoid shared bootstrap edits in this wave; if a missing prerequisite blocks the slice, record it exactly and mark blocked.
- You are not alone in the codebase. Do not revert others' edits. Adapt to concurrent changes.

## Acceptance Criteria

- Add real Playwright coverage for permission-group CRUD or effective edits plus menu/route effect after user re-login.
- Ensure the specs do not inject fake permission objects or mock route outcomes.
- Update the 2 owned docs from “待接入” to “已接入” with actual spec names and full-real-chain coverage notes.
- Add or update focused backend tests if backend permission behavior changes.
- Update `progress.md` at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

- 2026-04-05T05:04:11Z Rework guidance: the earlier blocker came from shared Playwright runtime state during parallel swarm work, not from a confirmed product-side missing prerequisite. Re-run targeted validation with isolated env values:
  `E2E_FRONTEND_BASE_URL=http://127.0.0.1:33102`
  `E2E_BACKEND_BASE_URL=http://127.0.0.1:38102`
  `E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\worker02_doc_auth.db`
  `E2E_BOOTSTRAP_SUMMARY_PATH=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth\bootstrap-summary-worker02.json`
  `E2E_AUTH_DIR=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth-worker02`
  `E2E_OUTPUT_DIR=D:\ProjectPackage\RagflowAuth\fronted\test-results\worker02`
  Continue validation and only re-block if the product still fails under isolated real env.

## Supervisor Notes

- Keep helper changes slice-local in `permissionGroupsFlow.js` where possible.
- If menu rendering depends on code outside owned paths, stop and report the exact file and issue instead of editing outside scope.
