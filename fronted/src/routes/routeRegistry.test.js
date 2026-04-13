import { APP_ROUTES, NAVIGATION_ROUTES, ROUTE_TEXT, findRouteConfig, getRouteTitle } from './routeRegistry';

describe('routeRegistry', () => {
  it('resolves alias and tool sub-route titles from shared metadata', () => {
    expect(getRouteTitle('/messages')).toBe(ROUTE_TEXT.nav.inbox);
    expect(getRouteTitle('/tools/package-drawing')).toBe(ROUTE_TEXT.toolTitles.packageDrawing);
  });

  it('keeps navigation-only entries separate from aliases', () => {
    const navPaths = NAVIGATION_ROUTES.map((route) => route.path);

    expect(navPaths).toContain('/tools');
    expect(navPaths).toContain('/inbox');
    expect(navPaths).toContain('/quality-system');
    expect(navPaths).not.toContain('/messages');
    expect(navPaths).not.toContain('/quality-system/training');
  });

  it('preserves special nav guard overrides in route metadata', () => {
    const dataSecurity = findRouteConfig('/data-security');
    const browser = findRouteConfig('/browser');
    const documentHistory = findRouteConfig('/document-history');
    const tools = findRouteConfig('/tools');
    const qualitySystem = findRouteConfig('/quality-system');

    expect(dataSecurity.guard.allowedRoles).toEqual(['admin', 'sub_admin']);
    expect(dataSecurity.navGuard.allowedRoles).toEqual(['admin']);
    expect(browser.navHiddenRoles).toEqual(['admin']);
    expect(documentHistory.guard.anyPermissions).toEqual([
      { resource: 'kb_documents', action: 'review' },
      { resource: 'kb_documents', action: 'view' },
    ]);
    expect(tools.matchPrefixes).toEqual(['/tools/']);
    expect(qualitySystem.guard.permission).toEqual({ resource: 'quality_system', action: 'view' });
    expect(qualitySystem.navGuard.allowedRoles).toEqual(['admin', 'sub_admin']);
    expect(qualitySystem.matchPrefixes).toEqual(['/quality-system/']);
  });

  it('keeps protected routes registered in the shared route list', () => {
    expect(APP_ROUTES.some((route) => route.path === '/notification-settings')).toBe(true);
    expect(APP_ROUTES.some((route) => route.path === '/approval-config')).toBe(true);
    expect(APP_ROUTES.some((route) => route.path === '/quality-system')).toBe(true);
    expect(APP_ROUTES.some((route) => route.path === '/quality-system/training')).toBe(true);
    expect(getRouteTitle('/quality-system/governance-closure')).toBe('\u6295\u8bc9\u4e0e\u6cbb\u7406\u95ed\u73af');
  });
});
