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

  it('passes transfer requests through the shared http client with the explicit contract', async () => {
    httpClient.requestJson.mockResolvedValue({ ok: true });

    await expect(documentBrowserApi.transferDocument('doc-1', 'KB-1', 'KB-2', 'copy')).resolves.toEqual({ ok: true });

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
});

