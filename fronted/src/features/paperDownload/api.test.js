import paperDownloadApi from './api';
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

describe('paperDownloadApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('sends paper download session requests through the feature API and keeps helper behavior stable', async () => {
    httpClient.requestJson.mockResolvedValueOnce({ session: { session_id: 'paper-session-1' } });

    expect(paperDownloadApi.parseKeywords('Alpha, beta\nalpha;Beta')).toEqual(['Alpha', 'beta']);
    expect(paperDownloadApi.parseKeywords('Alpha， beta；alpha')).toEqual(['Alpha', 'beta']);

    const result = await paperDownloadApi.createSession({
      keywordText: 'Alpha',
      useAnd: true,
      autoAnalyze: false,
      sources: { pubmed: { enabled: true, limit: 10 } },
    });

    expect(result).toEqual({ session: { session_id: 'paper-session-1' } });
    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/paper-download/sessions',
      {
        method: 'POST',
        body: JSON.stringify({
          keyword_text: 'Alpha',
          use_and: true,
          auto_analyze: false,
          sources: { pubmed: { enabled: true, limit: 10 } },
        }),
      }
    );
    expect(
      paperDownloadApi.toPreviewTarget('paper-session-1', {
        item_id: 'item-1',
        title: 'Paper Title',
        filename: 'paper.pdf',
      })
    ).toEqual({
      source: DOCUMENT_SOURCE.PAPER,
      docId: 'item-1',
      sessionId: 'paper-session-1',
      title: 'Paper Title',
      filename: 'paper.pdf',
    });
  });

  it('normalizes stop-session responses and fails fast on invalid payloads', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({
        result: {
          message: 'paper_download_session_stop_requested',
          session_id: 'paper-session-1',
          status: 'stopping',
          already_finished: false,
        },
      })
      .mockResolvedValueOnce({ result: { message: 'paper_download_session_stop_requested' } });

    await expect(paperDownloadApi.stopSession('paper-session-1')).resolves.toEqual({
      message: 'paper_download_session_stop_requested',
      session_id: 'paper-session-1',
      status: 'stopping',
      already_finished: false,
    });
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/paper-download/sessions/paper-session-1/stop',
      { method: 'POST' }
    );

    await expect(paperDownloadApi.stopSession('paper-session-2')).rejects.toThrow(
      'paper_download_stop_session_invalid_payload'
    );
  });

  it('uses the readable default local kb name when adding all papers to the local kb', async () => {
    httpClient.requestJson.mockResolvedValueOnce({ ok: true });

    await paperDownloadApi.addAllToLocalKb('paper-session-1');

    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/paper-download/sessions/paper-session-1/add-all-to-local-kb',
      {
        method: 'POST',
        body: JSON.stringify({ kb_ref: '[本地论文]' }),
      }
    );
  });
});
