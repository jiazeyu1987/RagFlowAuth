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
      .mockResolvedValueOnce({ allowed_extensions: ['.pdf'], updated_at_ms: 1 })
      .mockResolvedValueOnce({ allowed_extensions: ['.pdf', '.txt'], updated_at_ms: 2 });

    await expect(knowledgeUploadApi.getAllowedExtensions()).resolves.toEqual({
      allowedExtensions: ['.pdf'],
      updatedAtMs: 1,
    });
    await expect(knowledgeUploadApi.updateAllowedExtensions(['.pdf', '.txt'], 'test reason')).resolves.toEqual({
      allowedExtensions: ['.pdf', '.txt'],
      updatedAtMs: 2,
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

  it('fails fast when allowed-extensions payload does not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ allowed_extensions: '.pdf', updated_at_ms: 1 })
      .mockResolvedValueOnce({ allowed_extensions: ['.pdf'], updated_at_ms: '1' });

    await expect(knowledgeUploadApi.getAllowedExtensions()).rejects.toThrow(
      'knowledge_upload_allowed_extensions_get_invalid_payload'
    );
    await expect(knowledgeUploadApi.updateAllowedExtensions(['.pdf'], 'reason')).rejects.toThrow(
      'knowledge_upload_allowed_extensions_update_invalid_payload'
    );
  });
});
