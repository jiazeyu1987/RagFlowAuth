import { knowledgeUploadApi } from './api';
import { documentsApi } from '../../documents/api';
import { httpClient } from '../../../shared/http/httpClient';

jest.mock('../../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../documents/api', () => ({
  documentsApi: {
    uploadKnowledge: jest.fn(),
  },
}));

jest.mock('../../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('knowledgeUploadApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('loads and updates allowed extensions through the shared http client', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ allowed_extensions: ['.pdf'] })
      .mockResolvedValueOnce({ allowed_extensions: ['.pdf', '.txt'] });

    await expect(knowledgeUploadApi.getAllowedExtensions()).resolves.toEqual({ allowed_extensions: ['.pdf'] });
    await expect(knowledgeUploadApi.updateAllowedExtensions(['.pdf', '.txt'], 'test reason')).resolves.toEqual({
      allowed_extensions: ['.pdf', '.txt'],
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/knowledge/settings/allowed-extensions',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/knowledge/settings/allowed-extensions',
      {
        method: 'PUT',
        body: JSON.stringify({
          allowed_extensions: ['.pdf', '.txt'],
          change_reason: 'test reason',
        }),
      }
    );
  });

  it('routes document uploads through the documents feature api', async () => {
    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });
    documentsApi.uploadKnowledge.mockResolvedValue({ request_id: 'req-1' });

    await expect(knowledgeUploadApi.uploadDocument(file, 'KB-1')).resolves.toEqual({ request_id: 'req-1' });
    expect(documentsApi.uploadKnowledge).toHaveBeenCalledWith(file, 'KB-1');
  });
});

