import { searchConfigsApi } from './api';
import { httpClient } from '../../../shared/http/httpClient';

jest.mock('../../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('searchConfigsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps the config list to a stable array', async () => {
    httpClient.requestJson.mockResolvedValue({ configs: [{ id: 'cfg-1' }] });

    await expect(searchConfigsApi.listConfigs()).resolves.toEqual([{ id: 'cfg-1' }]);
  });

  it('fails fast when the config list payload does not match the backend contract', async () => {
    httpClient.requestJson.mockResolvedValue({ data: [] });

    await expect(searchConfigsApi.listConfigs()).rejects.toThrow('search_config_list_invalid_payload');
  });

  it('requires ok=true on delete operations', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false, detail: 'config_not_found' });

    await expect(searchConfigsApi.deleteConfig('cfg-1')).resolves.toBeUndefined();
    await expect(searchConfigsApi.deleteConfig('cfg-2')).rejects.toThrow('config_not_found');
  });
});

