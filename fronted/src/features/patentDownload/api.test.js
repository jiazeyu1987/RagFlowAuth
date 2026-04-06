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
    const response = { session: { session_id: 'patent-session-1' } };
    httpClient.requestJson.mockResolvedValue(response);

    expect(patentDownloadApi.parseKeywords('Alpha, beta\nalpha;Beta')).toEqual(['Alpha', 'beta']);

    const result = await patentDownloadApi.createSession({
      keywordText: 'Alpha',
      useAnd: false,
      autoAnalyze: true,
      sources: { google_patents: { enabled: true, limit: 20 } },
    });

    expect(result).toBe(response);
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
});
