import { electronicSignatureApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('electronicSignatureApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('requests a signature challenge through the electronic signature feature API', async () => {
    const response = { sign_token: 'sign-token-1' };
    httpClient.requestJson.mockResolvedValue(response);

    const result = await electronicSignatureApi.requestSignatureChallenge('SignPass123');

    expect(result).toBe(response);
    expect(httpClient.requestJson).toHaveBeenCalledWith(
      'http://auth.local/api/electronic-signatures/challenge',
      {
        method: 'POST',
        body: JSON.stringify({ password: 'SignPass123' }),
      }
    );
  });
});
