import authClient from './authClient';
import authApi from './auth/authApi';
import tokenStore from '../shared/auth/tokenStore';

jest.mock('./auth/authApi', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    logout: jest.fn(),
    getCurrentUser: jest.fn(),
    fetchWithAuth: jest.fn(),
    refreshAccessToken: jest.fn(),
  },
}));

jest.mock('../shared/auth/tokenStore', () => ({
  __esModule: true,
  default: {
    getAccessToken: jest.fn(),
    getRefreshToken: jest.fn(),
    getUser: jest.fn(),
    setAuth: jest.fn(),
    clearAuth: jest.fn(),
  },
}));

describe('authClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    authClient.accessToken = null;
    authClient.refreshToken = null;
    authClient.user = null;
  });

  it('stores login results into the session boundary', async () => {
    authApi.login.mockResolvedValue({
      access_token: 'access-1',
      refresh_token: 'refresh-1',
      user: { user_id: 'u-1', username: 'alice' },
    });

    const result = await authClient.login('alice', 'Secret123');

    expect(authApi.login).toHaveBeenCalledWith('alice', 'Secret123');
    expect(tokenStore.setAuth).toHaveBeenCalledWith(
      'access-1',
      'refresh-1',
      { user_id: 'u-1', username: 'alice' }
    );
    expect(authClient.accessToken).toBe('access-1');
    expect(authClient.refreshToken).toBe('refresh-1');
    expect(authClient.user).toEqual({ user_id: 'u-1', username: 'alice' });
    expect(result.user).toEqual({ user_id: 'u-1', username: 'alice' });
  });

  it('syncs refreshed tokens back from tokenStore', async () => {
    authApi.refreshAccessToken.mockResolvedValue('access-2');
    tokenStore.getAccessToken.mockReturnValue('access-2');
    tokenStore.getRefreshToken.mockReturnValue('refresh-2');
    tokenStore.getUser.mockReturnValue({ user_id: 'u-2', username: 'bob' });

    const result = await authClient.refreshAccessToken();

    expect(result).toBe('access-2');
    expect(authClient.accessToken).toBe('access-2');
    expect(authClient.refreshToken).toBe('refresh-2');
    expect(authClient.user).toEqual({ user_id: 'u-2', username: 'bob' });
  });
});
