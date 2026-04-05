# worker-08 Task

## Goal

根据 `doc/e2e/role/09_培训合规与审批资格.md` 新增一个多角色联动 Playwright 自动化测试，验证审批资格不足时被拦截，补录培训/认证后可继续审批。

## Owned Paths

- `fronted/e2e/tests/docs.role.training-approval-flow.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.role.training-approval-flow.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/role/09_培训合规与审批资格.md`
- Read `fronted/src/pages/ApprovalCenter.js`
- Read `fronted/src/pages/TrainingComplianceManagement.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js`

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover a blocked-approval state first, including the training help link if present
- Then simulate the trained/certified state and verify approval becomes actionable
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Keep the entire flow self-contained inside this owned spec file.
