# worker-05 Task

## Goal

落地数据安全与实用工具真实用例，覆盖 `doc/e2e/unit/数据安全.md`、`doc/e2e/unit/实用工具.md`，要求使用真实工具入口、真实权限可见性、真实备份或恢复能力；若真实能力缺失，必须定位并修复 owned slice 内缺口，不得 mock 成功结果。

## Owned Paths

- `fronted/e2e/tests/docs.data-security.spec.js`
- `fronted/e2e/tests/docs.tools.spec.js`
- `fronted/e2e/helpers/securityToolsFlow.js`
- `fronted/src/pages/DataSecurity.js`
- `fronted/src/pages/Tools.js`
- `fronted/src/pages/NMPATool.js`
- `fronted/src/features/dataSecurity/`
- `backend/app/modules/data_security/`
- `backend/app/modules/diagnostics/`
- `backend/app/modules/drug_admin/`
- `backend/tests/test_data_security*_unit.py`
- `doc/e2e/unit/数据安全.md`
- `doc/e2e/unit/实用工具.md`

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
- Use real tool cards, real internal navigation or external-link behavior, and real backup/restore records when available.
- If real backup or restore support is absent in this environment, fail fast with the exact missing prerequisite and update docs accordingly; do not fabricate completed backups.
- You are not alone in the codebase. Do not revert others' edits. Adapt to concurrent changes.

## Acceptance Criteria

- Add real Playwright coverage for tools page visibility/navigation and for data-security behavior if the real feature is available.
- Update the 2 owned docs from “待接入” to “已接入” only when true coverage lands; otherwise document the exact blocker precisely.
- Add or update focused backend tests if backend data-security or tool authorization behavior changes.
- Update `progress.md` at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

- 2026-04-05T05:16:35Z Corrective guidance: do not stop at a read-only findings report. This slice must either land real owned specs/docs or fail fast with an exact executed prerequisite gap after attempting the real flow. Treat `fronted/src/pages/Tools.js` static cards as current product behavior, not as permission to avoid implementation. Preferred path:
  1. Land `fronted/e2e/tests/docs.tools.spec.js` + `fronted/e2e/helpers/securityToolsFlow.js` against real login, real `canAccessTool` permission gating, real internal route navigation, and real external-link open behavior for existing tool cards.
  2. Attempt `fronted/e2e/tests/docs.data-security.spec.js` against the real admin-only backup/settings/restore-drill path using the worker-05 isolated env below.
  3. Only if the data-security slice still fails after an executed real run may you mark blocked, and then you must record the exact failing backend precondition or product bug from owned paths. Do not end with a generic audit summary.

## Supervisor Notes

- Keep helper changes slice-local in `securityToolsFlow.js`.
- When you run targeted Playwright locally in this swarm wave, use isolated env values to avoid cross-worker collisions:
  `E2E_FRONTEND_BASE_URL=http://127.0.0.1:33105`
  `E2E_BACKEND_BASE_URL=http://127.0.0.1:38105`
  `E2E_TEST_DB_PATH=D:\ProjectPackage\RagflowAuth\data\e2e\worker05_doc_auth.db`
  `E2E_BOOTSTRAP_SUMMARY_PATH=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth\bootstrap-summary-worker05.json`
  `E2E_AUTH_DIR=D:\ProjectPackage\RagflowAuth\fronted\e2e\.auth-worker05`
  `E2E_OUTPUT_DIR=D:\ProjectPackage\RagflowAuth\fronted\test-results\worker05`
