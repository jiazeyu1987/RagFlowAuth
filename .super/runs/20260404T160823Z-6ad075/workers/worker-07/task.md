# worker-07 Task

## Goal

根据 `doc/e2e/unit/文档记录.md` 为文档记录页面新增 Playwright 文档驱动自动化测试，覆盖文档记录、删除记录、下载记录三类页签与筛选/版本记录查看。

## Owned Paths

- `fronted/e2e/tests/docs.document-audit.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.document-audit.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/文档记录.md`
- Read `fronted/src/pages/DocumentAudit.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover the three tabs plus at least one filter/reset or version-history interaction supported by the page
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Prefer asserting current list content over visual styling details.
