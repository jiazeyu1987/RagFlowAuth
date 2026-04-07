# AGENTS.md

This file defines default rules for coding agents working in this repository.

## Goal

Deliver correct, bounded, and verifiable changes that fit the existing architecture and do not create hidden regressions elsewhere.

## Operating Principle

- Prefer the smallest safe change that solves the task.
- Understand the surrounding system before editing local code.
- Preserve global behavior unless the task explicitly requires behavior change.
- Favor incremental migration over hard switches when touching shared or risky code.
- Keep each change easy to review, test, and revert.

## Understand The Repository First

Before editing, identify:

- The relevant entry points, callers, consumers, and tests.
- The module or layer the target code belongs to.
- Existing patterns for naming, error handling, state flow, async behavior, and dependency direction.
- Whether the target code is local, shared, generated, vendor, packaging, or test-only code.

Do not assume a file is the correct place to implement logic only because the current task surfaced there.

## Architecture And Boundaries

- Respect existing module and layer boundaries.
- Do not introduce shortcuts across layers just to complete a task faster.
- Prefer adding logic in the layer that already owns that responsibility.
- Keep shared interfaces, schemas, and contracts stable unless change is necessary.
- If a contract changes, update callers, adapters, and verification together.
- Preserve backward compatibility when reasonable.

When the architecture is unclear, first infer it from neighboring code and usage patterns. If uncertainty remains, choose the least invasive approach.

## Coupling Control

- Prefer dependency on stable interfaces, adapters, and small utilities over direct dependency on concrete implementations.
- Do not introduce new cross-layer dependencies unless the task explicitly requires them.
- Keep data access, business rules, orchestration, presentation, and side effects separated where the existing architecture allows.
- Avoid passing large context objects through many layers when only a few values are needed.
- Avoid hidden coupling through globals, shared mutable state, implicit configuration, or convenience imports from distant modules.
- Do not duplicate similar logic in multiple modules when a local shared helper would reduce divergence.
- Do not centralize unrelated responsibilities into one manager, service, or utility just to avoid touching more than one file.
- If a function or class starts handling multiple reasons to change, split responsibilities before adding more logic.

Before introducing a new dependency, check:

- Whether the dependency direction matches the existing architecture.
- Whether the same goal can be achieved through an existing interface or nearby abstraction.
- Whether the new dependency will make testing, reuse, or future replacement harder.
- Whether the change couples two modules that should be able to evolve independently.

## Large File And Large Change Policy

- If a file is large, mixed-responsibility, or difficult to reason about, prefer narrow extraction before adding more logic.
- Extract a helper, utility, adapter, hook, class, or small module only when it reduces risk and improves change locality.
- Do not perform broad rewrites just because a file is messy.
- Keep refactor scope separate from feature scope unless combining them is required for safety.
- Avoid touching many files when one or two carefully chosen edits are sufficient.

If a task appears to require a broad rewrite, first look for a staged path:

1. Introduce a seam.
2. Move one responsibility.
3. Validate behavior.
4. Continue only if needed.

## Local Fix, Global Safety

A local pass is not enough. Every change must be checked against the surrounding system.

- Inspect upstream inputs and downstream consumers.
- Check representative call sites when changing shared code.
- Consider impact on configuration, lifecycle, state transitions, serialization, logging, and error propagation.
- Verify null handling, defaults, concurrency or async ordering, and cleanup behavior.
- Check whether tests cover only the edited function while missing integration risk in the call chain.

When the safest path is unclear, prefer:

- Adapter over replacement.
- Wrapper over invasive edit.
- Compatibility layer over immediate migration.
- Feature flag or staged rollout over global switch.

## Allowed Scope Of Change

- Modify only files directly relevant to the task.
- Do not mix feature work with unrelated cleanup, renaming, formatting churn, or speculative refactor.
- Do not change public behavior silently in adjacent flows.
- Do not edit generated, bundled, vendored, or third-party code unless the task explicitly requires it.
- Do not remove code only because it appears unused unless usage has been checked with reasonable confidence.

## Validation Strategy

Validation should expand outward from the point of change.

1. Run the narrowest meaningful test or check for the edited area.
2. Run a broader validation step for the surrounding module or package.
3. Run project-level checks when the change touches shared code, build configuration, packaging, or public contracts.

Use the checks that fit the stack, such as:

- Unit or focused tests.
- Integration or end-to-end tests for affected flows.
- Type checking.
- Linting.
- Build or compile verification.
- Packaging or startup verification where relevant.

If automated checks are unavailable, perform a concrete manual verification and state exactly what was checked.

Unverified assumptions must be reported as risk.

## Tests

- Add or update tests when fixing a bug, changing behavior, or touching critical logic.
- Prefer the nearest existing test style and location.
- Do not add low-value snapshot or superficial tests only to claim coverage.
- If a bug cannot be reproduced in tests yet, document the missing test gap explicitly.

## Code Quality

- Prefer straightforward code over clever compression.
- Keep functions and modules cohesive.
- Reuse existing utilities before introducing new abstractions.
- Introduce comments only where intent or constraints would otherwise be unclear.
- Avoid premature generalization.

## Risk Markers

Treat the following as high-risk and verify more broadly:

- Shared utility modules.
- Public interfaces and schemas.
- Authentication, authorization, permissions, or identity flows.
- Configuration loading and environment-dependent behavior.
- Serialization, persistence, migration, or network boundaries.
- Startup, shutdown, lifecycle, and background task logic.
- Packaging, deployment, installer, launcher, or release code.

## Communication Expectations

When reporting work, include:

- What changed.
- Why this approach was chosen.
- What was verified.
- What remains uncertain or unverified.
- Whether the change affects contracts, callers, or migration paths.

## Repository Notes

Use the repository structure to infer responsibility before editing.

- Inspect nearby source, tests, tools, and documentation before deciding where a change belongs.
- Treat packaged dependencies, generated outputs, external assets, build artifacts, and release files with extra caution.
- Prefer changing the module that owns the behavior instead of patching symptoms in an adjacent layer.

## Prohibited Defaults

- Do not make broad cosmetic rewrites.
- Do not bypass architecture without stating why.
- Do not assume a local green path means global safety.
- Do not rewrite a large file in place when a smaller decomposition reduces risk.
- Do not expand scope only because related cleanup looks convenient.
