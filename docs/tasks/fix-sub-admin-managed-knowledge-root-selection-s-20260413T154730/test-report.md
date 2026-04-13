# Test Report

- Task ID: `fix-sub-admin-managed-knowledge-root-selection-s-20260413T154730`
- Created: `2026-04-13T15:47:30`
- Workspace: `D:\ProjectPackage\RagflowAuth`
- User Request: `Fix sub-admin managed knowledge root selection so a new or edited sub-admin cannot see or select directories already assigned to other active sub-admins; enforce the rule in both UI and backend; add automated tests.`

## Environment Used

- Evaluation mode: same-agent constrained verification
- Validation surface: unit-runtime and real-browser
- Tools: pytest, react-scripts test, playwright
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: none
- Initial verdict before withheld inspection: yes

## Results

### T1: Frontend selection-state utility and selector rendering

- Result: passed
- Covers: P1-AC1, P1-AC3
- Command run: `npm test -- --runInBand --runTestsByPath src/features/users/utils/userManagedKbRoots.test.js src/features/users/components/KnowledgeRootNodeSelector.test.js src/features/users/hooks/useUserKnowledgeDirectories.test.js src/features/users/utils/userManagementMessages.test.js src/features/users/utils/userManagementState.test.js`
- Environment proof: local Jest runtime in `fronted/`
- Evidence refs: passing command output captured on 2026-04-13
- Notes: verified occupied subtree filtering, disabled ancestor containers, stale-assignment handling, and UI message mapping.

### T2: Backend overlap rejection

- Result: passed
- Covers: P1-AC2, P1-AC3
- Command run: `python -m pytest backend/tests/test_users_manager_manager_user_unit.py -q`
- Environment proof: local Python test runtime from repository root
- Evidence refs: passing command output captured on 2026-04-13
- Notes: verified create and update reject ancestor/descendant root overlap with `managed_kb_root_node_conflict` and `409`.

### T3: Browser regression for create-sub-admin modal

- Result: passed
- Covers: P1-AC1, P1-AC3
- Command run: `npx playwright test e2e/tests/admin.users.managed-kb-root-visibility.spec.js --workers=1`
- Environment proof: Playwright real browser against isolated frontend/backend ports `33003/38003`
- Evidence refs: passing Playwright run for `admin.users.managed-kb-root-visibility.spec.js`
- Notes: confirmed the create modal hides another sub-admin's occupied node, disables the shared ancestor container, and still exposes a free child.

### T4: Real doc user-management flow compatibility

- Result: passed
- Covers: P1-AC4
- Command run: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.user-management.spec.js --workers=1`
- Environment proof: Playwright doc bootstrap environment on `playwright.docs.config.js`
- Evidence refs: passing Playwright run for `docs.user-management.spec.js`
- Notes: confirmed the real flow now allocates an isolated managed root before creating the extra sub-admin and remains green.

### T5: Real doc permission-group flow compatibility

- Result: passed
- Covers: P1-AC4
- Command run: `npx playwright test --config playwright.docs.config.js e2e/tests/docs.permission-groups.folder-visibility.spec.js --workers=1`
- Environment proof: Playwright doc bootstrap environment on `playwright.docs.config.js`
- Evidence refs: passing Playwright run for `docs.permission-groups.folder-visibility.spec.js`
- Notes: confirmed the permission-group visibility flow stays green after switching the extra sub-admin to its own managed root.

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4
- Blocking prerequisites: none
- Summary: targeted frontend, backend, mocked browser, and doc real-chain regressions all passed after the managed-root isolation fix.

## Open Issues

- None.
