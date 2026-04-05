# worker-02 Task

## Goal

Validate the frontend behavior for the sub-admin knowledge-management refactor.
Focus on route visibility, permission gating, knowledge-base page behavior, permission-group UI usage of backend-trimmed trees, and user-management UI restrictions.

## Owned Paths

- `fronted/`
- `.super/runs/20260403T073650Z-98a4d5/workers/worker-02/`

## Do Not Modify

- All paths not listed in Owned Paths are out of scope unless the supervisor updates this file.

## Dependencies

- Backend is read-only context for API contracts and auth payload fields.
- Do not edit backend files.

## Acceptance Criteria

- Validation must pass.
- Supervisor review must pass.
- Update progress.md at required milestones.
- Produce a concise frontend verification report in progress.md covering:
- whether sub_admin can reach the intended pages
- whether UI actions are correctly hidden or enabled
- whether any page still infers subtree boundaries locally instead of consuming backend-trimmed data
- exact file references for findings

## Rework Entry

If validation fails, the supervisor will append rework instructions to this file.

## Supervisor Notes

- This is a review/validation task, not an implementation task unless a tiny isolated fix is necessary.
- Stop at ready_for_validation after writing findings.
