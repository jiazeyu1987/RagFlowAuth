import { chatConfigsApi } from './api';
import { httpClient } from '../../../shared/http/httpClient';

jest.mock('../../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('chatConfigsApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps the chat list to a stable array', async () => {
    httpClient.requestJson.mockResolvedValue({ chats: [{ id: 'chat-1' }] });

    await expect(chatConfigsApi.listChats({ page_size: 1000 })).resolves.toEqual([{ id: 'chat-1' }]);
  });

  it('fails fast when the chat list payload does not match the backend contract', async () => {
    httpClient.requestJson.mockResolvedValue({ data: [] });

    await expect(chatConfigsApi.listChats()).rejects.toThrow('ragflow_chat_list_invalid_payload');
  });

  it('requires ok=true on delete operations', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false, detail: 'chat_not_found' });

    await expect(chatConfigsApi.deleteChat('chat-1')).resolves.toBeUndefined();
    await expect(chatConfigsApi.deleteChat('chat-2')).rejects.toThrow('chat_not_found');
  });
});

