import { usersApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('usersApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes list-style user endpoints through the auth backend and returns stable arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce([{ user_id: 'u-1' }])
      .mockResolvedValueOnce([{ user_id: 'u-2' }])
      .mockResolvedValueOnce([{ user_id: 'u-3' }]);

    await expect(usersApi.list({ role: 'viewer', limit: 50 })).resolves.toEqual([{ user_id: 'u-1' }]);
    await expect(usersApi.items({ status: 'active' })).resolves.toEqual([{ user_id: 'u-2' }]);
    await expect(usersApi.search('alice', 10)).resolves.toEqual([{ user_id: 'u-3' }]);

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/users?role=viewer&limit=50',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/users?status=active',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/users?q=alice&limit=10',
      { method: 'GET' }
    );
  });

  it('passes through user mutation endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ user_id: 'u-1' })
      .mockResolvedValueOnce({ user_id: 'u-1' })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true });

    await expect(usersApi.create({ username: 'alice' })).resolves.toEqual({ user_id: 'u-1' });
    await expect(usersApi.update('u/1', { full_name: 'Alice' })).resolves.toEqual({ user_id: 'u-1' });
    await expect(usersApi.remove('u/1')).resolves.toEqual({ ok: true });
    await expect(usersApi.resetPassword('u/1', 'Secret123')).resolves.toEqual({ ok: true });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/users',
      {
        method: 'POST',
        body: JSON.stringify({ username: 'alice' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/users/u/1',
      {
        method: 'PUT',
        body: JSON.stringify({ full_name: 'Alice' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/users/u/1',
      {
        method: 'DELETE',
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/users/u/1/password',
      {
        method: 'PUT',
        body: JSON.stringify({ new_password: 'Secret123' }),
      }
    );
  });

  it('fails fast when user list endpoints do not return arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ users: [] });

    await expect(usersApi.list()).rejects.toThrow('users_list_invalid_payload');
    await expect(usersApi.items()).rejects.toThrow('users_items_invalid_payload');
    await expect(usersApi.search('alice')).rejects.toThrow('users_search_invalid_payload');
  });
});
