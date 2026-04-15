# Executor Prompt: WS06 Document Control Frontend Workspace

You are executing `WS06` under `docs/tasks/document-control-flow-parallel-20260414T151500`.

## Read First

1. `README.md`
2. `ws01-approval-workflow-contract.md`
3. `ws02-training-gate-and-ack-loop.md`
4. `ws03-controlled-release-and-distribution.md`
5. `ws04-department-ack-and-execution-confirmation.md`
6. `ws05-obsolete-retention-and-destruction.md`
7. `ws06-document-control-frontend-workspace.md`

## Mission

Replace the current document-control page pattern of directly exposing revision status transitions with a workflow workspace that only consumes stable backend contracts.

## Current Repo Facts

- `fronted/src/pages/DocumentControl.js` currently renders direct status transition buttons.
- The page does not show approval stage, training gate, release ledger, department acknowledgment, or obsolete-retention state.

## Owned Paths

- `fronted/src/pages/DocumentControl.js`
- `fronted/src/features/documentControl/`
- `fronted/src/pages/DocumentControl.test.js`
- `fronted/src/features/documentControl/useDocumentControlPage.test.js`
- `fronted/src/shared/errors/userFacingErrorMessages.js`

## Shared Integration Paths

- `fronted/src/routes/routeRegistry.js`
- `fronted/src/features/qualitySystem/moduleCatalog.js`
- `fronted/src/components/PermissionGuard.js`

## Must Deliver

- remove direct `Move to ...` status buttons
- introduce workflow-aware actions and sections
- render approval, training, release, department-ack, and obsolete-retention state
- preserve capability-based visibility
- add focused frontend tests

## Non-Goals

- backend workflow design
- backend training logic
- backend release ledger
- backend department acknowledgment model
- backend destruction scheduling

## Fail-Fast Rules

- If required backend endpoints are not available yet, stop and report the exact missing contract.
- Do not fake success states in the UI.
- Do not leave hidden legacy direct-transition behavior behind.

## Validation Target

```powershell
Set-Location 'D:\ProjectPackage\RagflowAuth\fronted'
$env:CI='true'
npm test -- --watch=false --runInBand DocumentControl.test.js useDocumentControlPage.test.js PermissionGuard.test.js
```

## Required Final Handoff

- changed paths
- user-visible workflow sections added
- validations run
- unresolved blockers
