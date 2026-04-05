# worker-06 Task

## Goal

根据 `doc/e2e/unit/电子签名管理.md` 为电子签名管理页面新增 Playwright 文档驱动自动化测试，覆盖签名资格开关、签名记录查看与验签动作。

## Owned Paths

- `fronted/e2e/tests/docs.electronic-signatures.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.electronic-signatures.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/电子签名管理.md`
- Read `fronted/src/pages/ElectronicSignatureManagement.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover at least one资格切换 action and one signature-record/verify action if the page exposes them
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- If the page exposes different wording than the doc, follow implementation and note the difference in progress.md.
