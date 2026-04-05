# worker-02 Task

## Goal

根据 `doc/e2e/unit/审批中心.md` 为审批中心页面新增 Playwright 文档驱动自动化测试，覆盖待我审批、我发起、审批通过、驳回、撤回及培训资格提示入口。

## Owned Paths

- `fronted/e2e/tests/docs.approval-center.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.approval-center.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/审批中心.md`
- Read `fronted/src/pages/ApprovalCenter.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js` and nearby approval-related specs

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover tab switching and the main action buttons from the doc where the page actually exposes them
- Include at least one training-help link assertion if the page renders that blocked state
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- If the doc wording differs from the page, follow current implementation and mention the divergence in progress.md.
