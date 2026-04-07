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

  it('loads a single user through the auth backend and returns a stable object', async () => {
    httpClient.requestJson.mockResolvedValueOnce({ user_id: 'u-1', username: 'alice' });

    await expect(usersApi.get('u-1')).resolves.toEqual({ user_id: 'u-1', username: 'alice' });

    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/users/u-1',
      { method: 'GET' }
    );
  });

  it('unwraps user mutation envelopes to stable objects', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ user: { user_id: 'u-1' } })
      .mockResolvedValueOnce({ user: { user_id: 'u-1' } })
      .mockResolvedValueOnce({ result: { message: 'user_deleted' } })
      .mockResolvedValueOnce({ result: { message: 'password_reset' } });

    await expect(usersApi.create({ username: 'alice' })).resolves.toEqual({ user_id: 'u-1' });
    await expect(usersApi.update('u/1', { full_name: 'Alice' })).resolves.toEqual({ user_id: 'u-1' });
    await expect(usersApi.remove('u/1')).resolves.toEqual({ message: 'user_deleted' });
    await expect(usersApi.resetPassword('u/1', 'Secret123')).resolves.toEqual({ message: 'password_reset' });

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

  it('fails fast when the user detail endpoint does not return an object', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce([{ user_id: 'u-1' }]);

    await expect(usersApi.get('u-1')).rejects.toThrow('users_get_invalid_payload');
    await expect(usersApi.get('u-2')).rejects.toThrow('users_get_invalid_payload');
  });

  it('fails fast when user mutation endpoints do not return the expected envelopes', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ user_id: 'u-1' })
      .mockResolvedValueOnce({ user_id: 'u-1' })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true });

    await expect(usersApi.create({ username: 'alice' })).rejects.toThrow('users_create_invalid_payload');
    await expect(usersApi.update('u/1', { full_name: 'Alice' })).rejects.toThrow('users_update_invalid_payload');
    await expect(usersApi.remove('u/1')).rejects.toThrow('users_remove_invalid_payload');
    await expect(usersApi.resetPassword('u/1', 'Secret123')).rejects.toThrow('users_reset_password_invalid_payload');
  });
});
