import { knowledgeApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../documents/api', () => ({
  DOCUMENT_SOURCE: {
    KNOWLEDGE: 'knowledge',
  },
  documentsApi: {
    uploadKnowledge: jest.fn(),
    deleteDocument: jest.fn(),
    downloadToBrowser: jest.fn(),
    batchDownloadKnowledgeToBrowser: jest.fn(),
  },
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('knowledgeApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('unwraps chat lists and search config lists to stable arrays', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ chats: [{ id: 'chat-1' }] })
      .mockResolvedValueOnce({ configs: [{ id: 'cfg-1' }] });

    await expect(knowledgeApi.listRagflowChats({ page_size: 1000 })).resolves.toEqual([{ id: 'chat-1' }]);
    await expect(knowledgeApi.listSearchConfigs()).resolves.toEqual([{ id: 'cfg-1' }]);
  });

  it('fails fast when list payloads do not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: { configs: [] } });

    await expect(knowledgeApi.listRagflowChats()).rejects.toThrow('ragflow_chat_list_invalid_payload');
    await expect(knowledgeApi.listSearchConfigs()).rejects.toThrow('search_config_list_invalid_payload');
  });

  it('requires ok=true on delete operations', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: false, detail: 'config_not_found' });

    await expect(knowledgeApi.deleteRagflowChat('chat-1')).resolves.toBeUndefined();
    await expect(knowledgeApi.deleteSearchConfig('cfg-1')).rejects.toThrow('config_not_found');
  });
});
