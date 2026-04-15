# LLM Dispatch Guide

- Task Root: `docs/tasks/document-control-flow-parallel-20260414T151500`
- Package Count: `6`
- Execution Mode: one LLM per package

## Read Order

Each executor LLM should read, in order:

1. `README.md`
2. Its assigned `ws*.md`
3. Its assigned `prompt-ws*.md`

## Assignment Map

- `WS01` -> `prompt-ws01-approval-workflow-contract.md`
- `WS02` -> `prompt-ws02-training-gate-and-ack-loop.md`
- `WS03` -> `prompt-ws03-controlled-release-and-distribution.md`
- `WS04` -> `prompt-ws04-department-ack-and-execution-confirmation.md`
- `WS05` -> `prompt-ws05-obsolete-retention-and-destruction.md`
- `WS06` -> `prompt-ws06-document-control-frontend-workspace.md`

## Global Rules

- Do not redefine the target workflow from scratch. Consume the assigned workstream contract.
- Do not add fallback, compatibility shims, or silent downgrade behavior.
- If a required dependency package is not finished, stop and report the exact blocker.
- Do not expand ownership beyond the declared `Owned Paths` except the listed shared integration paths.
- If multiple packages must touch the same shared integration path, keep that edit to the smallest possible registration or wiring change.

## Recommended Order

1. Execute `WS01`
2. Execute `WS02` and `WS03`
3. Execute `WS04` and `WS05`
4. Execute `WS06`

## Required Handoff Format

Each executor LLM should hand back:

- changed paths
- validations actually run
- blockers still open
- assumptions used
- whether the package is complete or needs another pass
