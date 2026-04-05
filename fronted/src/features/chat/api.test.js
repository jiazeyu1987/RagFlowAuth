import { chatApi } from './api';
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

describe('chatApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('sends streaming completion requests through the shared http client', async () => {
    const response = { ok: true };
    httpClient.request.mockResolvedValue(response);

    const result = await chatApi.requestCompletionStream('chat-1', {
      question: 'hello',
      sessionId: 'session-1',
      traceId: 'trace-1',
    });

    expect(result).toBe(response);
    expect(httpClient.request).toHaveBeenCalledWith(
      'http://auth.local/api/chats/chat-1/completions',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Chat-Trace-Id': 'trace-1',
        },
        body: JSON.stringify({
          question: 'hello',
          stream: true,
          session_id: 'session-1',
        }),
      }
    );
    expect(httpClient.requestJson).not.toHaveBeenCalled();
  });
});
