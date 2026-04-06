import patentDownloadApi from './api';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('patentDownloadApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('sends patent download session requests through the feature API and keeps helper behavior stable', async () => {
    httpClient.requestJson.mockResolvedValueOnce({ session: { session_id: 'patent-session-1' } });

    expect(patentDownloadApi.parseKeywords('Alpha, beta\nalpha;Beta')).toEqual(['Alpha', 'beta']);

    const result = await patentDownloadApi.createSession({
      keywordText: 'Alpha',
      useAnd: false,
      autoAnalyze: true,
      sources: { google_patents: { enabled: true, limit: 20 } },
    });

    expect(result).toEqual({ session: { session_id: 'patent-session-1' } });
    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/patent-download/sessions',
      {
        method: 'POST',
        body: JSON.stringify({
          keyword_text: 'Alpha',
          use_and: false,
          auto_analyze: true,
          sources: { google_patents: { enabled: true, limit: 20 } },
        }),
      }
    );
    expect(
      patentDownloadApi.toPreviewTarget('patent-session-1', {
        item_id: 'item-1',
        title: 'Patent Title',
        filename: 'patent.pdf',
      })
    ).toEqual({
      source: DOCUMENT_SOURCE.PATENT,
      docId: 'item-1',
      sessionId: 'patent-session-1',
      title: 'Patent Title',
      filename: 'patent.pdf',
    });
  });

  it('normalizes stop-session responses and fails fast on invalid payloads', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({
        result: {
          message: 'patent_download_session_already_finished',
          session_id: 'patent-session-1',
          status: 'completed',
          already_finished: true,
        },
      })
      .mockResolvedValueOnce({ result: { message: 'patent_download_session_stop_requested' } });

    await expect(patentDownloadApi.stopSession('patent-session-1')).resolves.toEqual({
      message: 'patent_download_session_already_finished',
      session_id: 'patent-session-1',
      status: 'completed',
      already_finished: true,
    });
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/patent-download/sessions/patent-session-1/stop',
      { method: 'POST' }
    );

    await expect(patentDownloadApi.stopSession('patent-session-2')).rejects.toThrow(
      'patent_download_stop_session_invalid_payload'
    );
  });
});
