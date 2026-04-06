import { knowledgeApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../documents/api', () => ({
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

  it('unwraps the dataset list to a stable array', async () => {
    httpClient.requestJson.mockResolvedValue({ datasets: [{ id: 'ds-1' }] });

    await expect(knowledgeApi.listRagflowDatasets()).resolves.toEqual([{ id: 'ds-1' }]);
  });

  it('fails fast when the dataset list payload does not match the backend contract', async () => {
    httpClient.requestJson.mockResolvedValue({ data: [] });

    await expect(knowledgeApi.listRagflowDatasets()).rejects.toThrow('ragflow_dataset_list_invalid_payload');
  });
});
