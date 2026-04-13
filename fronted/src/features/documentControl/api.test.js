import documentControlApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('documentControlApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes list and document envelopes for all document-control endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ controlled_document_id: 'doc-1' }] })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', title: 'URS' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', current_revision_id: 'rev-2' } })
      .mockResolvedValueOnce({ document: { controlled_document_id: 'doc-1', effective_revision_id: 'rev-2' } });

    await expect(
      documentControlApi.listDocuments({
        limit: 20,
        docCode: 'DOC-1',
        title: 'URS',
        documentType: 'urs',
        productName: 'Product A',
        registrationRef: 'REG-001',
        status: 'draft',
        query: 'validation',
      })
    ).resolves.toEqual([{ controlled_document_id: 'doc-1' }]);

    await expect(documentControlApi.getDocument('doc-1')).resolves.toEqual({
      controlled_document_id: 'doc-1',
      title: 'URS',
    });

    const createPayload = {
      doc_code: 'DOC-002',
      title: 'SRS',
      document_type: 'srs',
      target_kb_id: 'Quality KB',
      file: new File(['hello'], 'srs.md', { type: 'text/markdown' }),
    };
    await expect(documentControlApi.createDocument(createPayload)).resolves.toEqual({
      controlled_document_id: 'doc-2',
    });

    const revisionPayload = {
      change_summary: 'rev 2',
      file: new File(['rev2'], 'srs-v2.md', { type: 'text/markdown' }),
    };
    await expect(documentControlApi.createRevision('doc-1', revisionPayload)).resolves.toEqual({
      controlled_document_id: 'doc-1',
      current_revision_id: 'rev-2',
    });

    await expect(
      documentControlApi.transitionRevision('rev-2', { target_status: 'effective' })
    ).resolves.toEqual({
      controlled_document_id: 'doc-1',
      effective_revision_id: 'rev-2',
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/quality-system/doc-control/documents?limit=20&doc_code=DOC-1&title=URS&document_type=urs&product_name=Product+A&registration_ref=REG-001&status=draft&query=validation',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/quality-system/doc-control/documents',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/quality-system/doc-control/documents/doc-1/revisions',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/quality-system/doc-control/revisions/rev-2/transitions',
      {
        method: 'POST',
        body: JSON.stringify({ target_status: 'effective' }),
      }
    );
  });

  it('fails fast when payload shapes do not match the page contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ count: 1 })
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ item: {} })
      .mockResolvedValueOnce({ result: {} });

    await expect(documentControlApi.listDocuments()).rejects.toThrow(
      'document_control_documents_list_invalid_payload'
    );
    await expect(documentControlApi.getDocument('doc-1')).rejects.toThrow(
      'document_control_document_get_invalid_payload'
    );
    await expect(documentControlApi.createDocument({})).rejects.toThrow(
      'document_control_document_create_invalid_payload'
    );
    await expect(documentControlApi.createRevision('doc-1', {})).rejects.toThrow(
      'document_control_revision_create_invalid_payload'
    );
    await expect(documentControlApi.transitionRevision('rev-1', {})).rejects.toThrow(
      'document_control_revision_transition_invalid_payload'
    );
  });
});
