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
    setAccessToken: jest.fn(),
    getRefreshToken: jest.fn(),
    setRefreshToken: jest.fn(),
    getUser: jest.fn(),
    setUser: jest.fn(),
    setAuth: jest.fn(),
    clearAuth: jest.fn(),
  },
}));

describe('authClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    tokenStore.getAccessToken.mockReturnValue(null);
    tokenStore.getRefreshToken.mockReturnValue(null);
    tokenStore.getUser.mockReturnValue(null);
  });

  it('stores login results into the session boundary', async () => {
    authApi.login.mockResolvedValue({
      access_token: 'access-1',
      refresh_token: 'refresh-1',
      user: { user_id: 'u-1', username: 'alice' },
    });

    const result = await authClient.login('alice', 'Secret123');

    tokenStore.getAccessToken.mockReturnValue('access-1');
    tokenStore.getRefreshToken.mockReturnValue('refresh-1');
    tokenStore.getUser.mockReturnValue({ user_id: 'u-1', username: 'alice' });

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

  it('reads refreshed tokens directly from tokenStore', async () => {
    authApi.refreshAccessToken.mockResolvedValue('access-2');

    const result = await authClient.refreshAccessToken();

    tokenStore.getAccessToken.mockReturnValue('access-2');
    tokenStore.getRefreshToken.mockReturnValue('refresh-2');
    tokenStore.getUser.mockReturnValue({ user_id: 'u-2', username: 'bob' });

    expect(result).toBe('access-2');
    expect(authClient.accessToken).toBe('access-2');
    expect(authClient.refreshToken).toBe('refresh-2');
    expect(authClient.user).toEqual({ user_id: 'u-2', username: 'bob' });
  });

  it('persists current-user refreshes back into tokenStore', async () => {
    tokenStore.getAccessToken.mockReturnValue('access-3');
    authApi.getCurrentUser.mockResolvedValue({ user_id: 'u-3', username: 'carol' });

    const result = await authClient.getCurrentUser();

    tokenStore.getUser.mockReturnValue({ user_id: 'u-3', username: 'carol' });

    expect(tokenStore.setUser).toHaveBeenCalledWith({ user_id: 'u-3', username: 'carol' });
    expect(result).toEqual({ user_id: 'u-3', username: 'carol' });
    expect(authClient.user).toEqual({ user_id: 'u-3', username: 'carol' });
  });
});
