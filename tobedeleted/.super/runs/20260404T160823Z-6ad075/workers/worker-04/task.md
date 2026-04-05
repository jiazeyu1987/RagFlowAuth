# worker-04 Task

## Goal

根据 `doc/e2e/unit/站内信.md` 为站内信页面新增 Playwright 文档驱动自动化测试，覆盖未读过滤、全部已读、单条已读切换与跳转入口展示。

## Owned Paths

- `fronted/e2e/tests/docs.inbox.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.inbox.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/站内信.md`
- Read `fronted/src/pages/InboxPage.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover unread toggle/filter, mark-all-read, and at least one item-level action from the page
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Keep selectors explicit and prefer existing `data-testid` attributes.
