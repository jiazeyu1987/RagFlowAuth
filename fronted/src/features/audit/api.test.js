import { auditApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('auditApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps document audit list endpoints to stable arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ documents: [{ doc_id: 'doc-1' }] })
      .mockResolvedValueOnce({ deletions: [{ doc_id: 'doc-2' }] })
      .mockResolvedValueOnce({ downloads: [{ doc_id: 'doc-3' }] });

    await expect(auditApi.listDocuments({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-1' }]);
    await expect(auditApi.listDeletions({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-2' }]);
    await expect(auditApi.listDownloads({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-3' }]);
  });

  it('normalizes document versions payload to a stable object shape', async () => {
    httpClient.requestJson.mockResolvedValue({
      versions: [{ doc_id: 'doc-1-v2' }],
      current_doc_id: 'doc-1-v2',
      logical_doc_id: 'logical-1',
    });

    await expect(auditApi.listDocumentVersions('doc-1')).resolves.toEqual({
      versions: [{ doc_id: 'doc-1-v2' }],
      currentDocId: 'doc-1-v2',
      logicalDocId: 'logical-1',
    });
  });
});

