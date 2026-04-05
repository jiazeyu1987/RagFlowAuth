# worker-01 Task

## Goal

根据 `doc/e2e/unit/培训合规.md` 为培训合规页面新增 Playwright 文档驱动自动化测试，覆盖页签切换、目标用户选择、保存培训记录、保存上岗认证等核心动作。

## Owned Paths

- `fronted/e2e/tests/docs.training-compliance.spec.js`

## Do Not Modify

- Any path outside `fronted/e2e/tests/docs.training-compliance.spec.js`
- Shared runner or manifest files such as `fronted/package.json`, `scripts/`, or `*.bat`
- Existing E2E specs unless the supervisor updates this file

## Dependencies

- Read `doc/e2e/unit/培训合规.md`
- Read `fronted/src/pages/TrainingComplianceManagement.js`
- Reuse the local E2E style from `fronted/e2e/helpers/auth.js` and existing specs

## Acceptance Criteria

- Add one new spec file with one or more tests tagged `@doc-e2e`
- Use mocked network responses; do not depend on real backend data
- Cover refresh-visible state, tab switching, target-user selection, save training record, and save certification
- Keep all helpers inline in this file unless absolutely necessary
- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- You are not alone in the codebase. Do not revert other workers' edits.
- Prefer focused page-level coverage driven by the doc wording, not exhaustive backend behavior.
