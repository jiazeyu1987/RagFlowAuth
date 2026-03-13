# Definition of Done (DoD) Template

Use this checklist in each task/PR.

## Basic Info
- Task ID:
- Requirement IDs (RTM):
- Owner:
- Reviewer:
- Priority:

## Design & Scope
- [ ] Scope confirmed and mapped to RTM requirement IDs.
- [ ] API/schema/UI impacts are listed.
- [ ] Backward compatibility impact is assessed.

## Implementation
- [ ] Code implemented according to agreed scope.
- [ ] Feature flags added if rollout risk exists.
- [ ] Error handling and observability (logs/metrics) added.
- [ ] Security constraints are applied (authz/input validation/data access boundaries).

## Tests
- [ ] Unit tests added/updated.
- [ ] Integration tests added/updated.
- [ ] E2E tests added/updated when user-visible behavior changed.
- [ ] Security tests added/updated when policy/auth/data rules changed.
- [ ] Performance/stability tests run for heavy/background workflows.

## Validation Evidence
- [ ] Test run commands documented.
- [ ] Key outputs attached (pass/fail summary).
- [ ] Manual verification steps documented where needed.

## Documentation
- [ ] API docs updated.
- [ ] User/admin docs updated.
- [ ] `todolist.md` status updated.
- [ ] RTM status updated (implemented/partial/planned).

## Release Readiness
- [ ] Migration scripts prepared and rollback path validated.
- [ ] Monitoring/alerts verified in target env.
- [ ] Rollout plan and fallback plan reviewed.

## Done Criteria
- [ ] All mandatory checks above passed.
- [ ] Reviewer approved.
- [ ] Linked requirement can be accepted by test evidence.
