# Sub-Admin Managed Knowledge Root Isolation

- Task ID: `fix-sub-admin-managed-knowledge-root-selection-s-20260413T154730`
- Created: `2026-04-13T15:47:30`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Fix sub-admin managed knowledge root selection so a new or edited sub-admin cannot see or select directories already assigned to other active sub-admins; enforce the rule in both UI and backend; add automated tests.`

## Goal

Ensure a newly created or edited sub-admin cannot see or select knowledge-directory roots that are already assigned to other active sub-admins in the same company, and ensure backend writes fail fast if a conflicting root is submitted directly to the API.

## Scope

- User-management create/edit sub-admin modal flow in `fronted/src/features/users/**`.
- Managed knowledge-root selector state derivation and node disabling.
- Backend sub-admin create/update validation in `backend/services/users/**`.
- Automated coverage for utility logic, selector rendering, backend manager validation, and browser regression tests.

## Non-Goals

- Changing permission-group folder visibility behavior beyond keeping its existing doc E2E compatible with the new backend constraint.
- Adding fallback behavior for stale or conflicting assignments.
- Reworking the knowledge-directory API shape or tenant-resolution model.

## Preconditions

- Frontend Jest environment must be runnable from `fronted/`.
- Backend unit tests must run against the local Python environment.
- Playwright local browser runtime must be available for the mocked admin regression test.
- Doc E2E bootstrap environment must be runnable for `playwright.docs.config.js`.

## Impacted Areas

- `fronted/src/features/users/hooks/useKnowledgeDirectoryListing.js`
- `fronted/src/features/users/components/KnowledgeRootNodeSelector.js`
- `fronted/src/features/users/utils/userManagedKbRoots.js`
- `backend/services/users/manager_support.py`
- `backend/tests/test_users_manager_manager_user_unit.py`
- `fronted/e2e/tests/admin.users.managed-kb-root-visibility.spec.js`
- `fronted/e2e/tests/docs.user-management.spec.js`
- `fronted/e2e/tests/docs.permission-groups.folder-visibility.spec.js`

## Phase Plan

### P1: Frontend, Backend, and Regression Coverage

- Objective:
  Ship the managed-root isolation rule end to end for sub-admin create/edit flows.
- Owned paths:
  `fronted/src/features/users/**`
  `backend/services/users/manager_support.py`
  `backend/tests/test_users_manager_manager_user_unit.py`
  `fronted/e2e/tests/admin.users.managed-kb-root-visibility.spec.js`
  `fronted/e2e/tests/docs.user-management.spec.js`
  `fronted/e2e/tests/docs.permission-groups.folder-visibility.spec.js`
- Dependencies:
  Existing user-management page, knowledge-directory APIs, and doc E2E bootstrap fixtures.
- Deliverables:
  Frontend hidden/disabled managed-root behavior, backend overlap rejection, updated browser regressions, and passing targeted tests.

## Phase Acceptance Criteria

### P1

- P1-AC1: In the create/edit sub-admin UI, directories already assigned to other active sub-admins in the same company are either hidden or rendered as non-selectable containers, while still allowing navigation to free descendants.
- P1-AC2: Backend user create/update flows reject overlapping managed knowledge-root assignments for active same-company sub-admins with a `409` conflict.
- P1-AC3: Automated tests cover frontend selection-state logic, selector rendering, backend validation, and at least one browser regression for the create flow.
- P1-AC4: Existing doc E2E coverage that creates extra sub-admins remains green under the new backend conflict rule.
- Evidence expectation:
  `execution-log.md` and `test-report.md` record the code changes plus unit/browser commands that passed on April 13, 2026.

## Done Definition

- The create/edit sub-admin selector no longer exposes other sub-admins' occupied knowledge roots as selectable options.
- API writes cannot bypass the UI and assign overlapping managed roots.
- Targeted frontend unit tests, backend unit tests, the new mocked Playwright regression, and the updated real doc E2E specs all pass.

## Blocking Conditions

- Playwright or doc bootstrap runtime unavailable.
- Knowledge-directory API stops returning stable node ids or paths.
- User-management backend cannot resolve managed root paths for submitted nodes.
