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

  it('unwraps strict config envelopes for detail and mutation endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ config: { id: 'cfg-1', name: 'Config 1', config: {} } })
      .mockResolvedValueOnce({ config: { id: 'cfg-2', name: 'Config 2', config: {} } })
      .mockResolvedValueOnce({ config: { id: 'cfg-2', name: 'Config 2 updated', config: {} } });

    await expect(searchConfigsApi.getConfig('cfg-1')).resolves.toEqual({
      id: 'cfg-1',
      name: 'Config 1',
      config: {},
    });
    await expect(searchConfigsApi.createConfig({ name: 'Config 2', config: {} })).resolves.toEqual({
      id: 'cfg-2',
      name: 'Config 2',
      config: {},
    });
    await expect(searchConfigsApi.updateConfig('cfg-2', { name: 'Config 2 updated', config: {} })).resolves.toEqual({
      id: 'cfg-2',
      name: 'Config 2 updated',
      config: {},
    });
  });

  it('fails fast when the config list payload does not match the backend contract', async () => {
    httpClient.requestJson.mockResolvedValue({ data: [] });

    await expect(searchConfigsApi.listConfigs()).rejects.toThrow('search_config_list_invalid_payload');
  });

  it('fails fast when config detail or mutation envelopes are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ id: 'cfg-1' })
      .mockResolvedValueOnce({ config: [] });

    await expect(searchConfigsApi.getConfig('cfg-1')).rejects.toThrow('search_config_get_invalid_payload');
    await expect(searchConfigsApi.createConfig({ name: 'Config 1', config: {} })).rejects.toThrow(
      'search_config_create_invalid_payload'
    );
  });

  it('requires ok=true on delete operations', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false, detail: 'config_not_found' });

    await expect(searchConfigsApi.deleteConfig('cfg-1')).resolves.toBeUndefined();
    await expect(searchConfigsApi.deleteConfig('cfg-2')).rejects.toThrow('config_not_found');
  });
});
