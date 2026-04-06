import { documentsApi, DOCUMENT_SOURCE } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    request: jest.fn(),
    requestJson: jest.fn(),
  },
}));

describe('documentsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'info').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('loads ragflow previews through the documents feature api', async () => {
    const response = {
      ok: true,
      json: jest.fn().mockResolvedValue({ type: 'text', content: 'hello' }),
      headers: { get: jest.fn().mockReturnValue('req-1') },
    };
    httpClient.request.mockResolvedValue(response);

    await expect(
      documentsApi.preview({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId: 'doc-1',
        datasetName: 'KB-A',
      })
    ).resolves.toEqual({ type: 'text', content: 'hello' });

    expect(httpClient.request).toHaveBeenCalledWith(
      'http://auth.local/api/preview/documents/ragflow/doc-1/preview?dataset=KB-A',
      { method: 'GET' }
    );
  });

  it('downloads knowledge documents as blobs through the shared http client', async () => {
    const blob = new Blob(['binary'], { type: 'application/pdf' });
    const response = {
      ok: true,
      blob: jest.fn().mockResolvedValue(blob),
      headers: { get: jest.fn().mockReturnValue('req-2') },
    };
    httpClient.request.mockResolvedValue(response);

    await expect(
      documentsApi.downloadBlob({
        source: DOCUMENT_SOURCE.KNOWLEDGE,
        docId: 'doc-2',
      })
    ).resolves.toBe(blob);

    expect(httpClient.request).toHaveBeenCalledWith(
      'http://auth.local/api/documents/knowledge/doc-2/download',
      { method: 'GET' }
    );
  });

  it('uploads knowledge documents through the feature api boundary', async () => {
    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });
    httpClient.requestJson.mockResolvedValue({ request_id: 'req-3' });

    await expect(documentsApi.uploadKnowledge(file, 'KB-1')).resolves.toEqual({ request_id: 'req-3' });

    expect(httpClient.requestJson).toHaveBeenCalledTimes(1);
    const [url, options] = httpClient.requestJson.mock.calls[0];
    expect(url).toBe('http://auth.local/api/documents/knowledge/upload?kb_id=KB-1');
    expect(options.method).toBe('POST');
    expect(options.includeContentType).toBe(false);
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('file')).toBe(file);
  });
});
