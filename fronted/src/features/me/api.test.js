import meApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('meApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps my knowledge bases into a stable camelCase object', async () => {
    httpClient.requestJson.mockResolvedValue({
      kbs: {
        kb_ids: ['kb-1', 'kb-2'],
        kb_names: ['KB 1', 'KB 2'],
      },
    });

    await expect(meApi.listMyKnowledgeBases()).resolves.toEqual({
      kbIds: ['kb-1', 'kb-2'],
      kbNames: ['KB 1', 'KB 2'],
    });

    expect(httpClient.requestJson).toHaveBeenCalledWith('http://auth.local/api/me/kbs', {
      method: 'GET',
    });
  });

  it('fails fast when my knowledge bases payload does not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ kb_ids: [] })
      .mockResolvedValueOnce({ kbs: { kb_ids: [] } });

    await expect(meApi.listMyKnowledgeBases()).rejects.toThrow('me_kbs_invalid_payload');
    await expect(meApi.listMyKnowledgeBases()).rejects.toThrow('me_kbs_invalid_payload');
  });

  it('keeps change password on the auth endpoint and unwraps the result envelope', async () => {
    httpClient.requestJson.mockResolvedValue({ result: { message: 'password_changed' } });

    await expect(meApi.changePassword('old-pass', 'new-pass')).resolves.toEqual({
      message: 'password_changed',
    });

    expect(httpClient.requestJson).toHaveBeenCalledWith('http://auth.local/api/auth/password', {
      method: 'PUT',
      body: JSON.stringify({
        old_password: 'old-pass',
        new_password: 'new-pass',
      }),
    });
  });

  it('fails fast when the password-change payload does not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ message: 'password_changed' })
      .mockResolvedValueOnce({ result: {} });

    await expect(meApi.changePassword('old-pass', 'new-pass')).rejects.toThrow(
      'me_change_password_invalid_payload'
    );
    await expect(meApi.changePassword('old-pass', 'new-pass')).rejects.toThrow(
      'me_change_password_invalid_payload'
    );
  });
});
