# worker-03 Task

## Goal

落地搜索、智能对话、越权隔离真实用例，覆盖 `doc/e2e/unit/全库搜索.md`、`doc/e2e/unit/智能对话.md`、`doc/e2e/role/11_越权访问与数据隔离.md`，要求使用真实知识库、真实已发布文档、真实检索结果、真实会话与真实权限差异。

## Owned Paths

- `fronted/e2e/tests/docs.global-search.spec.js`
- `fronted/e2e/tests/docs.chat.spec.js`
- `fronted/e2e/tests/docs.role.data-isolation.spec.js`
- `fronted/e2e/helpers/searchChatFlow.js`
- `fronted/src/pages/Chat.js`
- `fronted/src/pages/SearchConfigsPanel.js`
- `fronted/src/features/chat/`
- `backend/app/modules/chat/`
- `backend/app/modules/agents/`
- `backend/app/modules/search_configs/`
- `backend/app/modules/user_chat_permissions/`
- `backend/tests/test_chat*_unit.py`
- `doc/e2e/unit/全库搜索.md`
- `doc/e2e/unit/智能对话.md`
- `doc/e2e/role/11_越权访问与数据隔离.md`

## Do Not Modify

- `doc/e2e/manifest.json`
- `doc/e2e/README.md`
- `doc/e2e/unit/README.md`
- `doc/e2e/role/README.md`
- `scripts/check_doc_e2e_docs.py`
- `scripts/run_doc_e2e.py`
- `scripts/bootstrap_doc_test_env.py`
- `fronted/src/pages/PermissionGroupManagement.js`
- Any other paths not listed in Owned Paths are out of scope unless the supervisor updates this file.

## Dependencies

- Validation contract: `VALIDATION.md`
- Use real published documents and real user authorization boundaries. Do not stub answers or search hits.
- If the environment lacks a real chat prerequisite, fail fast: record the exact missing service or credential and mark blocked instead of inventing a default response.
- You are not alone in the codebase. Do not revert others' edits. Adapt to concurrent changes.

## Acceptance Criteria

- Add real Playwright coverage for search hit visibility and at least one real chat flow or, if blocked by missing prerequisite, produce a precise blocker rooted in owned code and docs.
- Add real isolation coverage showing route/menu/data or search/chat result differences between accounts.
- Update the 3 owned docs from “待接入” to “已接入” only if true coverage lands; otherwise document the exact blocker without fallback.
- Add or update focused backend tests if backend authorization or chat behavior changes.
- Update `progress.md` at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- Keep new helpers slice-local in `searchChatFlow.js`.
- This slice is allowed to use existing real search helpers but should not edit shared helpers unless absolutely necessary and explicitly recorded in progress.
- When you run targeted Playwright locally in this swarm wave, use isolated env values to avoid cross-worker collisions:
  `E2E_FRONTEND_BASE_URL=http://127.0.0.1:33103`
  `E2E_BACKEND_BASE_URL=http://127.0.0.1:38103`
  `E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\worker03_doc_auth.db`
  `E2E_BOOTSTRAP_SUMMARY_PATH=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth\bootstrap-summary-worker03.json`
  `E2E_AUTH_DIR=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth-worker03`
  `E2E_OUTPUT_DIR=D:\ProjectPackage\RagflowAuth\fronted\test-results\worker03`
