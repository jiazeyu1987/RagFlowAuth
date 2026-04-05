# worker-03 Task

## Goal

根据 `doc/e2e/unit/审批配置.md` 为审批配置页面新增 Playwright 文档驱动自动化测试，覆盖流程选择、步骤编辑、成员配置与保存。

## Owned Paths

- `fronted/e2e/tests/docs.approval-config.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.approval-config.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/审批配置.md`
- Read `fronted/src/pages/ApprovalConfig.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover operation type selection, adding/editing steps or members, and save success/error behavior that matches the page
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Stay within the owned spec file even if you notice helper refactor opportunities.
