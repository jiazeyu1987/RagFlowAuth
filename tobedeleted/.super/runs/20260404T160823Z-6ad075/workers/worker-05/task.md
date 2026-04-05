# worker-05 Task

## Goal

根据 `doc/e2e/unit/通知设置.md` 为通知设置页面新增 Playwright 文档驱动自动化测试，覆盖规则配置、基础渠道配置、发送历史查询与重试/重发动作。

## Owned Paths

- `fronted/e2e/tests/docs.notification-settings.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.notification-settings.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/通知设置.md`
- Read `fronted/src/pages/NotificationSettings.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover at least one rule-save path, one channel-save path, one history query path, and one job action path
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Match the current UI text and test IDs even if the doc uses broader business wording.
