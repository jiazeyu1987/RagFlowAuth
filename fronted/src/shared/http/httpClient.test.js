import { httpClient } from './httpClient';
import tokenStore from '../auth/tokenStore';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

describe('httpClient unauthorized handling', () => {
  const originalFetch = global.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    jest.restoreAllMocks();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        pathname: '/approval-center',
        assign: jest.fn(),
        href: '/approval-center',
      },
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    });
  });

  it('does not clear auth or redirect for sign token business 401', async () => {
    tokenStore.setAuth('access-token', 'refresh-token', { user_id: 'u1' });
    global.fetch = jest.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'sign_token_invalid' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(
      httpClient.requestJson('/api/operation-approvals/requests/r-1/approve', {
        method: 'POST',
        body: JSON.stringify({ sign_token: 'bad-token' }),
      })
    ).rejects.toMatchObject({ status: 401, message: 'sign_token_invalid' });

    expect(tokenStore.getAccessToken()).toBe('access-token');
    expect(tokenStore.getRefreshToken()).toBe('refresh-token');
    expect(window.location.assign).not.toHaveBeenCalled();
  });

  it('clears auth and redirects for real session 401', async () => {
    tokenStore.setAuth('access-token', 'refresh-token', { user_id: 'u1' });
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Invalid access token' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'invalid_refresh_token:expired' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      );

    await expect(
      httpClient.requestJson('/api/operation-approvals/requests/r-1/approve', {
        method: 'POST',
        body: JSON.stringify({ sign_token: 'token-1' }),
      })
    ).rejects.toMatchObject({ status: 401 });

    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith('/login');
  });
});
