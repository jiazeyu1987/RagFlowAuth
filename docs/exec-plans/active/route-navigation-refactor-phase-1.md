# Route Navigation Refactor Phase 1

## Context

The permission-model tranche removed duplicated permission semantics, but the frontend still
keeps route metadata in more than one place:

- `fronted/src/App.js` declares paths, components, and route guards inline.
- `fronted/src/components/Layout.js` separately declares navigation labels, icons, page titles,
  hidden-role rules, and some route-specific visibility logic.

That duplication means adding or changing a page still requires touching multiple locations,
which raises regression risk after every permission or navigation update.

## In Scope

- `fronted/src/App.js`
- `fronted/src/components/Layout.js`
- a new shared route-registry module
- focused frontend tests for navigation visibility and route metadata helpers

## Out Of Scope

- document-browser and preview decomposition
- auth semantics redesign beyond the already completed capability adapter
- page-specific UI rewrites
- backend changes

## Refactor Direction

1. Introduce one route registry that owns path, title, icon, guard metadata, and nav inclusion.
2. Make `App.js` render guarded routes from that registry instead of hardcoding them inline.
3. Make `Layout.js` consume the same registry for nav entries and header-title resolution.
4. Keep special-case nav behavior explicit in route metadata, not scattered in layout code.

## Acceptance Criteria

1. Adding a standard page no longer requires parallel updates in both `App.js` and `Layout.js`.
2. Nav labels, header titles, and route guard metadata come from one route-registry source.
3. Existing route paths, nav visibility, title rendering, and inbox alias behavior remain stable.

## Validation

- `$env:CI='true'; npm test -- --runInBand --watchAll=false src/components/Layout.test.js src/components/PermissionGuard.test.js src/routes/routeRegistry.test.js`
