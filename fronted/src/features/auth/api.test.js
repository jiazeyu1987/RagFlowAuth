import authApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    refreshAccessToken: jest.fn(),
    requestJson: jest.fn(),
  },
}));

describe('authApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('logs in through the auth backend and hydrates the current user', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ access_token: 'access-1', refresh_token: 'refresh-1' })
      .mockResolvedValueOnce({ user_id: 'u-1', username: 'alice' });

    await expect(authApi.login('alice', 'Secret123')).resolves.toEqual({
      access_token: 'access-1',
      refresh_token: 'refresh-1',
      user: { user_id: 'u-1', username: 'alice' },
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/auth/login',
      {
        method: 'POST',
        skipAuth: true,
        skipRefresh: true,
        body: JSON.stringify({ username: 'alice', password: 'Secret123' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/auth/me',
      {
        headers: { Authorization: 'Bearer access-1' },
        skipRefresh: true,
      }
    );
  });

  it('delegates session operations to the shared http client', async () => {
    httpClient.refreshAccessToken.mockResolvedValue({ access_token: 'access-2' });
    httpClient.requestJson
      .mockResolvedValueOnce({ result: { message: 'logout_ok' } })
      .mockResolvedValueOnce({ user_id: 'u-2' });

    await expect(authApi.refreshAccessToken()).resolves.toEqual({ access_token: 'access-2' });
    await expect(authApi.logout()).resolves.toEqual({ message: 'logout_ok' });
    await expect(authApi.getCurrentUser({ skipRefresh: true })).resolves.toEqual({ user_id: 'u-2' });

    expect(httpClient.refreshAccessToken).toHaveBeenCalledTimes(1);
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/auth/logout',
      {
        method: 'POST',
        skipRefresh: true,
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/auth/me',
      {
        method: 'GET',
        skipRefresh: true,
      }
    );
  });

  it('fails fast when logout returns an invalid payload', async () => {
    httpClient.requestJson.mockResolvedValue({ message: 'logout_ok' });

    await expect(authApi.logout()).rejects.toThrow('auth_logout_invalid_payload');
  });
});
