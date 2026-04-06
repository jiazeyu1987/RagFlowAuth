import { act, renderHook, waitFor } from '@testing-library/react';
import { useAuth } from '../../../hooks/useAuth';
import { chatConfigsApi } from './api';
import { knowledgeApi } from '../../knowledge/api';
import useChatConfigsPanelPage from './useChatConfigsPanelPage';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('./api', () => ({
  chatConfigsApi: {
    listChats: jest.fn(),
    getChat: jest.fn(),
    createChat: jest.fn(),
    updateChat: jest.fn(),
    deleteChat: jest.fn(),
    clearParsedFiles: jest.fn(),
  },
}));

jest.mock('../../knowledge/api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
  },
}));

describe('useChatConfigsPanelPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });
    chatConfigsApi.listChats.mockResolvedValue([
      { id: 'c1', name: 'Chat 1', description: 'desc' },
      { id: 'hidden', name: '大模型', description: 'hidden' },
    ]);
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds1', name: 'KB 1', chunk_count: 3, document_count: 1 },
    ]);
    chatConfigsApi.getChat.mockResolvedValue({
      id: 'c1',
      name: 'Chat 1',
      dataset_ids: ['ds1'],
    });
  });

  it('loads visible chat configs and the first chat detail into stable hook state', async () => {
    const { result } = renderHook(() => useChatConfigsPanelPage());

    await waitFor(() => {
      expect(result.current.chatList.map((chat) => chat.id)).toEqual(['c1']);
      expect(result.current.chatSelected?.id).toBe('c1');
      expect(result.current.chatNameText).toBe('Chat 1');
      expect(result.current.selectedDatasetIds).toEqual(['ds1']);
    });

    expect(chatConfigsApi.listChats).toHaveBeenCalledWith({ page_size: 1000 });
    expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalledTimes(1);
    expect(chatConfigsApi.getChat).toHaveBeenCalledWith('c1');
  });

  it('creates a blank chat payload with name only', async () => {
    chatConfigsApi.createChat.mockResolvedValue({
      id: 'c2',
      name: 'New Chat',
    });
    chatConfigsApi.getChat
      .mockResolvedValueOnce({
        id: 'c1',
        name: 'Chat 1',
        dataset_ids: ['ds1'],
      })
      .mockResolvedValueOnce({
        id: 'c2',
        name: 'New Chat',
        dataset_ids: [],
      });
    chatConfigsApi.listChats
      .mockResolvedValueOnce([{ id: 'c1', name: 'Chat 1', description: 'desc' }])
      .mockResolvedValueOnce([
        { id: 'c1', name: 'Chat 1', description: 'desc' },
        { id: 'c2', name: 'New Chat', description: '' },
      ]);

    const { result } = renderHook(() => useChatConfigsPanelPage());

    await waitFor(() => expect(result.current.chatSelected?.id).toBe('c1'));

    act(() => {
      result.current.openCreate();
      result.current.setCreateName('New Chat');
    });

    await act(async () => {
      await result.current.createChat();
    });

    expect(chatConfigsApi.createChat).toHaveBeenCalledWith({ name: 'New Chat' });
    expect(result.current.createOpen).toBe(false);
    expect(result.current.chatSelected?.id).toBe('c2');
  });
});
