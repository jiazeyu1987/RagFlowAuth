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

  it('normalizes audit list endpoints to stable objects and arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ total: 2, items: [{ id: 'event-1' }, { id: 'event-2' }] })
      .mockResolvedValueOnce({ documents: [{ doc_id: 'doc-1' }] })
      .mockResolvedValueOnce({ deletions: [{ doc_id: 'doc-2' }] })
      .mockResolvedValueOnce({ downloads: [{ doc_id: 'doc-3' }] });

    await expect(auditApi.listEvents({ limit: 10, offset: 5 })).resolves.toEqual({
      total: 2,
      items: [{ id: 'event-1' }, { id: 'event-2' }],
    });
    await expect(auditApi.listDocuments({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-1' }]);
    await expect(auditApi.listDeletions({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-2' }]);
    await expect(auditApi.listDownloads({ limit: 10 })).resolves.toEqual([{ doc_id: 'doc-3' }]);

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/audit/events?limit=10&offset=5',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/knowledge/documents?limit=10',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/knowledge/deletions?limit=10',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/ragflow/downloads?limit=10',
      { method: 'GET' }
    );
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

  it('fails fast when audit payloads do not match the feature contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ total: '2', items: [] })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({ downloads: {} })
      .mockResolvedValueOnce({ current_doc_id: 'doc-1' });

    await expect(auditApi.listEvents()).rejects.toThrow('audit_events_list_invalid_payload');
    await expect(auditApi.listDocuments()).rejects.toThrow('audit_documents_list_invalid_payload');
    await expect(auditApi.listDeletions()).rejects.toThrow('audit_deletions_list_invalid_payload');
    await expect(auditApi.listDownloads()).rejects.toThrow('audit_downloads_list_invalid_payload');
    await expect(auditApi.listDocumentVersions('doc-1')).rejects.toThrow(
      'audit_document_versions_list_invalid_payload'
    );
  });
});
