import { getDefaultLandingRoute } from './defaultLandingRoute';

describe('getDefaultLandingRoute', () => {
  it('returns logs for admin users', () => {
    expect(getDefaultLandingRoute({ role: 'admin' })).toBe('/logs');
  });

  it('returns chat for non-admin users', () => {
    expect(getDefaultLandingRoute({ role: 'sub_admin' })).toBe('/chat');
    expect(getDefaultLandingRoute({ role: 'viewer' })).toBe('/chat');
    expect(getDefaultLandingRoute(null)).toBe('/chat');
  });
});
