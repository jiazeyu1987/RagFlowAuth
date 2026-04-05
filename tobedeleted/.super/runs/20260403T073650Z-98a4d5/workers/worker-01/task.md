# worker-01 Task

## Goal

Validate the backend implementation of the sub-admin knowledge-management refactor.
Focus on permission enforcement, route integration, schema/model coverage, and concrete risks or gaps.

## Owned Paths

- `backend/`
- `.super/runs/20260403T073650Z-98a4d5/workers/worker-01/`

## Do Not Modify

- All paths not listed in Owned Paths are out of scope unless the supervisor updates this file.

## Dependencies

- Read-only dependency on frontend behavior only when needed for API usage assumptions.
- Do not edit frontend files.

## Acceptance Criteria

- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.
- Produce a concise backend verification report in progress.md covering:
- route coverage for `/api/knowledge/directories`, `/api/datasets`, permission-group KB scope checks, and user group assignment checks
- any concrete bugs, missing enforcement, or missing tests
- exact file references for findings

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- This is a review/validation task, not an implementation task unless you find a small, self-contained fix that is clearly required.
- If you find a bug, state whether it is blocking or non-blocking.
- Stop at ready_for_validation after writing findings.
