# Permission Model Refactor Phase 1

## Context

This document is the active execution plan for stage 4 of the system refactor roadmap:
permission-model consolidation. The current system already has a backend source of truth
in `backend/app/core/permission_resolver.py`, but the frontend still re-derives permission
meaning in multiple places:

- `/api/auth/me` returns raw flags and scope fragments, but not a stable capability payload.
- `fronted/src/hooks/useAuth.js` rebuilds policy decisions with a large inline `can(...)`.
- `fronted/src/components/PermissionGuard.js` adds another interpretation layer on top.
- route declarations mix role checks and permission checks without a shared adapter.

Phase 1 keeps the refactor bounded. The goal is to remove duplicated permission semantics
without rewriting the full route registry or redesigning permission-group storage.

## In Scope

- `backend/app/core/permission_resolver.py`
- `backend/services/auth_me_service.py`
- `backend/app/modules/auth/router.py`
- permission-related backend tests around `/api/auth/me` and resolver output
- `fronted/src/hooks/useAuth.js`
- `fronted/src/components/PermissionGuard.js`
- a new frontend auth capability adapter/helper module
- focused frontend tests for auth capability evaluation and guard behavior

## Explicitly Out Of Scope

- full route registry consolidation in `fronted/src/App.js`
- permission-group schema redesign
- backend authorization changes outside the existing resolver truth source
- rewriting every page to consume a new auth API directly
- fallback branches for missing capability payloads

## Refactor Direction

### 1. Backend emits a stable capability payload

Add a normalized capability structure to `/api/auth/me` that represents permissions as
`resource -> action -> scope/targets`, with the backend resolver remaining the only policy
truth source.

### 2. Frontend consumes capability payload through one adapter

Create a focused auth capability helper on the frontend that:

- validates the capability payload
- evaluates `resource/action/target` checks
- keeps unspecified capabilities denied by default

### 3. `useAuth.can()` becomes a compatibility facade

Keep the public `useAuth.can(resource, action, target)` API so existing pages do not need
to be rewritten, but make it delegate to the normalized capability adapter instead of
re-encoding rules inline.

### 4. `PermissionGuard` delegates to normalized auth logic

Remove duplicate permission interpretation from `PermissionGuard` and let it call a single
auth authorization helper backed by normalized capability data.

## Deliverables

1. `/api/auth/me` includes `capabilities`.
2. Frontend auth state normalizes and stores `capabilities`.
3. `useAuth.can()` no longer contains resource-specific policy branching.
4. `PermissionGuard` uses shared authorization evaluation.
5. Focused backend and frontend regression tests cover the new contract.

## Acceptance Criteria

1. Adding or changing a permission rule for the covered resources requires backend resolver
   changes plus at most one frontend adapter update, not multiple UI-specific branches.
2. `/api/auth/me` keeps existing fields (`permissions`, `accessible_kbs`, `accessible_kb_ids`,
   `accessible_chats`) and adds `capabilities` without changing route or envelope behavior.
3. Frontend route guards and tool access checks continue to behave the same for admin,
   sub-admin, viewer, and scoped-tool users.
4. No fallback or silent downgrade is introduced for missing capability data. Invalid auth
   payloads fail fast.

## Validation

- Backend:
  - `python -m pytest backend/tests/test_auth_me_service_unit.py backend/tests/test_auth_me_admin.py backend/tests/test_permissions_none_defaults.py backend/tests/test_permission_resolver_tools_scope_unit.py backend/tests/test_permission_resolver_tool_guard_unit.py backend/tests/test_permission_resolver_sub_admin_management_unit.py`
- Frontend:
  - `$env:CI='true'; npm test -- --runInBand --watchAll=false src/hooks/useAuth.test.js src/components/Layout.test.js src/components/PermissionGuard.test.js`

## Risks And Controls

- Risk: the new payload shape drifts from resolver truth.
  - Control: capabilities are built directly from `PermissionSnapshot`-derived values.
- Risk: frontend mock payloads miss `capabilities` and begin failing.
  - Control: update focused auth tests in the same tranche; keep failure explicit.
- Risk: scoped tool access or KB visibility changes subtly.
  - Control: preserve existing `permissions` and `accessible_*` fields and test scoped/all/none cases.
