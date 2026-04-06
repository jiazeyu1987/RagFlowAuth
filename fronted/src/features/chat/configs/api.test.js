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

  it('unwraps strict chat envelopes for detail and mutation endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ chat: { id: 'chat-1', name: 'Chat 1' } })
      .mockResolvedValueOnce({ chat: { id: 'chat-2', name: 'Chat 2' } })
      .mockResolvedValueOnce({ chat: { id: 'chat-2', name: 'Chat 2 updated' } })
      .mockResolvedValueOnce({ chat: { id: 'chat-2', name: 'Chat 2 updated' } });

    await expect(chatConfigsApi.getChat('chat-1')).resolves.toEqual({ id: 'chat-1', name: 'Chat 1' });
    await expect(chatConfigsApi.createChat({ name: 'Chat 2' })).resolves.toEqual({ id: 'chat-2', name: 'Chat 2' });
    await expect(chatConfigsApi.updateChat('chat-2', { name: 'Chat 2 updated' })).resolves.toEqual({
      id: 'chat-2',
      name: 'Chat 2 updated',
    });
    await expect(chatConfigsApi.clearParsedFiles('chat-2')).resolves.toEqual({
      id: 'chat-2',
      name: 'Chat 2 updated',
    });
  });

  it('fails fast when the chat list payload does not match the backend contract', async () => {
    httpClient.requestJson.mockResolvedValue({ data: [] });

    await expect(chatConfigsApi.listChats()).rejects.toThrow('ragflow_chat_list_invalid_payload');
  });

  it('fails fast when chat detail or mutation envelopes are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ id: 'chat-1' })
      .mockResolvedValueOnce({ chat: [] });

    await expect(chatConfigsApi.getChat('chat-1')).rejects.toThrow('ragflow_chat_get_invalid_payload');
    await expect(chatConfigsApi.createChat({ name: 'Chat 1' })).rejects.toThrow('ragflow_chat_create_invalid_payload');
  });

  it('unwraps delete result envelopes and propagates backend failures', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ result: { message: 'chat_deleted' } })
      .mockRejectedValueOnce(new Error('chat_not_found'));

    await expect(chatConfigsApi.deleteChat('chat-1')).resolves.toEqual({ message: 'chat_deleted' });
    await expect(chatConfigsApi.deleteChat('chat-2')).rejects.toThrow('chat_not_found');
  });

  it('fails fast when the delete payload does not include a result message', async () => {
    httpClient.requestJson.mockResolvedValue({ ok: true });

    await expect(chatConfigsApi.deleteChat('chat-1')).rejects.toThrow('ragflow_chat_delete_invalid_payload');
  });
});
