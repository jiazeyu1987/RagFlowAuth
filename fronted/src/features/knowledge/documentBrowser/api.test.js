import { documentBrowserApi } from './api';
import { httpClient } from '../../../shared/http/httpClient';

jest.mock('../../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('documentBrowserApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps the ragflow document list to a stable array', async () => {
    httpClient.requestJson.mockResolvedValue({ documents: [{ id: 'doc-1' }] });

    await expect(documentBrowserApi.listDocuments('KB-1')).resolves.toEqual([{ id: 'doc-1' }]);
  });

  it('fails fast when the ragflow document list payload is invalid', async () => {
    httpClient.requestJson.mockResolvedValue({ items: [] });

    await expect(documentBrowserApi.listDocuments('KB-1')).rejects.toThrow(
      'ragflow_document_list_invalid_payload'
    );
  });

  it('requires an explicit dataset name for list/status/detail/delete requests', async () => {
    await expect(documentBrowserApi.listDocuments()).rejects.toThrow('missing_dataset_name');
    await expect(documentBrowserApi.getDocumentStatus('doc-1')).rejects.toThrow('missing_dataset_name');
    await expect(documentBrowserApi.getDocumentDetail('doc-1')).rejects.toThrow('missing_dataset_name');
    await expect(documentBrowserApi.deleteDocument('doc-1')).rejects.toThrow('missing_dataset_name');

    expect(httpClient.requestJson).not.toHaveBeenCalled();
  });

  it('unwraps document status and detail envelopes to stable objects', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ status: { doc_id: 'doc-1', status: 'finished' } })
      .mockResolvedValueOnce({ document: { id: 'doc-1', name: 'Doc 1' } });

    await expect(documentBrowserApi.getDocumentStatus('doc-1', 'KB-1')).resolves.toEqual({
      docId: 'doc-1',
      status: 'finished',
    });
    await expect(documentBrowserApi.getDocumentDetail('doc-1', 'KB-1')).resolves.toEqual({
      id: 'doc-1',
      name: 'Doc 1',
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/ragflow/documents/doc-1/status?dataset_name=KB-1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/ragflow/documents/doc-1?dataset_name=KB-1',
      { method: 'GET' }
    );
  });

  it('fails fast when status or detail payloads are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ doc_id: 'doc-1', status: 'finished' })
      .mockResolvedValueOnce({ document: [] });

    await expect(documentBrowserApi.getDocumentStatus('doc-1', 'KB-1')).rejects.toThrow(
      'ragflow_document_status_get_invalid_payload'
    );
    await expect(documentBrowserApi.getDocumentDetail('doc-1', 'KB-1')).rejects.toThrow(
      'ragflow_document_detail_get_invalid_payload'
    );
  });

  it('passes delete requests through the feature api boundary with the explicit contract', async () => {
    httpClient.requestJson.mockResolvedValue({ result: { message: 'document_deleted' } });

    await expect(documentBrowserApi.deleteDocument('doc-1', 'KB-1')).resolves.toEqual({
      message: 'document_deleted',
    });

    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/ragflow/documents/doc-1?dataset_name=KB-1',
      { method: 'DELETE' }
    );
  });

  it('fails fast when delete payload is invalid', async () => {
    httpClient.requestJson.mockResolvedValue({ message: 'document_deleted' });

    await expect(documentBrowserApi.deleteDocument('doc-1', 'KB-1')).rejects.toThrow(
      'ragflow_document_delete_invalid_payload'
    );
  });

  it('passes transfer requests through the shared http client with the explicit contract', async () => {
    httpClient.requestJson.mockResolvedValue({
      result: {
        ok: true,
        operation: 'copy',
        source_dataset_name: 'KB-1',
        target_dataset_name: 'KB-2',
        source_doc_id: 'doc-1',
        target_doc_id: 'doc-target-1',
        filename: 'Doc 1',
        source_deleted: false,
        parse_triggered: true,
        parse_error: '',
      },
    });

    await expect(documentBrowserApi.transferDocument('doc-1', 'KB-1', 'KB-2', 'copy')).resolves.toEqual({
      ok: true,
      operation: 'copy',
      sourceDatasetName: 'KB-1',
      targetDatasetName: 'KB-2',
      sourceDocId: 'doc-1',
      targetDocId: 'doc-target-1',
      filename: 'Doc 1',
      sourceDeleted: false,
      parseTriggered: true,
      parseError: '',
    });

    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/ragflow/documents/doc-1/transfer',
      {
        method: 'POST',
        body: JSON.stringify({
          source_dataset_name: 'KB-1',
          target_dataset_name: 'KB-2',
          operation: 'copy',
        }),
      }
    );
  });

  it('fails fast when transfer payload is invalid', async () => {
    httpClient.requestJson.mockResolvedValue({ result: { ok: true, operation: 'copy' } });

    await expect(documentBrowserApi.transferDocument('doc-1', 'KB-1', 'KB-2', 'copy')).rejects.toThrow(
      'ragflow_document_transfer_invalid_payload'
    );
  });

  it('passes batch transfer requests through the shared http client with the explicit contract', async () => {
    httpClient.requestJson.mockResolvedValue({
      result: {
        ok: false,
        operation: 'move',
        total: 2,
        success_count: 1,
        failed_count: 1,
        results: [
          {
            ok: true,
            operation: 'move',
            source_dataset_name: 'KB-1',
            target_dataset_name: 'KB-2',
            source_doc_id: 'doc-1',
            target_doc_id: 'doc-target-1',
            filename: 'Doc 1',
            source_deleted: true,
            parse_triggered: true,
            parse_error: '',
          },
        ],
        failed: [
          {
            doc_id: 'doc-2',
            source_dataset_name: 'KB-1',
            target_dataset_name: 'KB-2',
            detail: 'document_not_found',
          },
        ],
      },
    });

    await expect(
      documentBrowserApi.transferDocumentsBatch(
        [
          { docId: 'doc-1', sourceDatasetName: 'KB-1', targetDatasetName: 'KB-2' },
          { docId: 'doc-2', sourceDatasetName: 'KB-1', targetDatasetName: 'KB-2' },
        ],
        'move'
      )
    ).resolves.toEqual({
      ok: false,
      operation: 'move',
      total: 2,
      successCount: 1,
      failedCount: 1,
      results: [
        {
          ok: true,
          operation: 'move',
          sourceDatasetName: 'KB-1',
          targetDatasetName: 'KB-2',
          sourceDocId: 'doc-1',
          targetDocId: 'doc-target-1',
          filename: 'Doc 1',
          sourceDeleted: true,
          parseTriggered: true,
          parseError: '',
        },
      ],
      failed: [
        {
          docId: 'doc-2',
          sourceDatasetName: 'KB-1',
          targetDatasetName: 'KB-2',
          detail: 'document_not_found',
        },
      ],
    });

    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/ragflow/documents/transfer/batch',
      {
        method: 'POST',
        body: JSON.stringify({
          operation: 'move',
          items: [
            {
              doc_id: 'doc-1',
              source_dataset_name: 'KB-1',
              target_dataset_name: 'KB-2',
            },
            {
              doc_id: 'doc-2',
              source_dataset_name: 'KB-1',
              target_dataset_name: 'KB-2',
            },
          ],
        }),
      }
    );
  });

  it('fails fast when batch transfer payload is invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({
        result: {
          ok: true,
          operation: 'copy',
          total: 1,
          success_count: 1,
          failed_count: 0,
          results: [{ source_dataset_name: 'KB-1' }],
          failed: [],
        },
      });

    await expect(
      documentBrowserApi.transferDocumentsBatch(
        [{ docId: 'doc-1', sourceDatasetName: 'KB-1', targetDatasetName: 'KB-2' }],
        'copy'
      )
    ).rejects.toThrow('ragflow_document_transfer_batch_invalid_payload');
    await expect(
      documentBrowserApi.transferDocumentsBatch(
        [{ docId: 'doc-1', sourceDatasetName: 'KB-1', targetDatasetName: 'KB-2' }],
        'copy'
      )
    ).rejects.toThrow('ragflow_document_transfer_batch_invalid_payload');
  });
});
