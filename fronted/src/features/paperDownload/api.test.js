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
    const response = { session: { session_id: 'paper-session-1' } };
    httpClient.requestJson.mockResolvedValue(response);

    expect(paperDownloadApi.parseKeywords('Alpha, beta\nalpha;Beta')).toEqual(['Alpha', 'beta']);

    const result = await paperDownloadApi.createSession({
      keywordText: 'Alpha',
      useAnd: true,
      autoAnalyze: false,
      sources: { pubmed: { enabled: true, limit: 10 } },
    });

    expect(result).toBe(response);
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
});
