import { knowledgeApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../documents/api', () => ({
  DOCUMENT_SOURCE: {
    KNOWLEDGE: 'knowledge',
  },
  documentsApi: {
    uploadKnowledge: jest.fn(),
    deleteDocument: jest.fn(),
    downloadToBrowser: jest.fn(),
    batchDownloadKnowledgeToBrowser: jest.fn(),
  },
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('knowledgeApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps list endpoints to stable arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ datasets: [{ id: 'ds-1' }] })
      .mockResolvedValueOnce({ configs: [{ id: 'cfg-1' }] });

    await expect(knowledgeApi.listRagflowDatasets()).resolves.toEqual([{ id: 'ds-1' }]);
    await expect(knowledgeApi.listSearchConfigs()).resolves.toEqual([{ id: 'cfg-1' }]);
  });

  it('fails fast when list payloads do not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { configs: [] } });

    await expect(knowledgeApi.listRagflowDatasets()).rejects.toThrow('ragflow_dataset_list_invalid_payload');
    await expect(knowledgeApi.listSearchConfigs()).rejects.toThrow('search_config_list_invalid_payload');
  });

  it('requires ok=true on search config delete operations', async () => {
    httpClient.requestJson.mockResolvedValue({ ok: false, detail: 'config_not_found' });

    await expect(knowledgeApi.deleteSearchConfig('cfg-1')).rejects.toThrow('config_not_found');
  });
});
