import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ChatConfigsPanel } from './ChatConfigsPanel';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/knowledge/api', () => ({
  knowledgeApi: {
    listRagflowChats: jest.fn(),
    listRagflowDatasets: jest.fn(),
    getRagflowChat: jest.fn(),
    createRagflowChat: jest.fn(),
    updateRagflowChat: jest.fn(),
    deleteRagflowChat: jest.fn(),
    clearRagflowChatParsedFiles: jest.fn(),
  },
}));

describe('ChatConfigsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    knowledgeApi.listRagflowChats.mockResolvedValue([{ id: 'c1', name: 'Chat 1', description: 'desc' }]);
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds1', name: 'KB 1', chunk_count: 3, document_count: 1 },
    ]);
    knowledgeApi.getRagflowChat.mockResolvedValue({
      id: 'c1',
      name: 'Chat 1',
      dataset_ids: ['ds1'],
    });
  });

  it('allows sub_admin to create and edit chats', async () => {
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    expect(screen.getByTestId('chat-config-new')).toBeInTheDocument();
    expect(screen.getByTestId('chat-config-save')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('chat-config-new'));
    expect(screen.getByTestId('chat-config-create-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('chat-config-create-confirm')).not.toBeDisabled();
    expect(screen.queryByTestId('chat-config-create-from')).not.toBeInTheDocument();
  });

  it('opens create dialog without cloning the first existing chat', async () => {
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    const detailCallsBeforeOpen = knowledgeApi.getRagflowChat.mock.calls.length;

    fireEvent.click(screen.getByTestId('chat-config-new'));

    expect(screen.getByTestId('chat-config-create-dialog')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-config-create-from')).not.toBeInTheDocument();
    expect(knowledgeApi.getRagflowChat).toHaveBeenCalledTimes(detailCallsBeforeOpen);
  });

  it('creates a blank chat payload with name only', async () => {
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });
    knowledgeApi.createRagflowChat.mockResolvedValue({
      id: 'c2',
      name: 'New Chat',
    });
    knowledgeApi.getRagflowChat
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

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    fireEvent.click(screen.getByTestId('chat-config-new'));
    fireEvent.change(screen.getByTestId('chat-config-create-name'), { target: { value: 'New Chat' } });
    fireEvent.click(screen.getByTestId('chat-config-create-confirm'));

    await waitFor(() => expect(knowledgeApi.createRagflowChat).toHaveBeenCalledWith({ name: 'New Chat' }));
  });

  it('disables unparsed knowledge bases in the selection list', async () => {
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds_unready', name: 'KB Unready', chunk_count: 0, document_count: 0 },
    ]);
    knowledgeApi.getRagflowChat.mockResolvedValue({
      id: 'c1',
      name: 'Chat 1',
      dataset_ids: [],
    });

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    expect(screen.getByTestId('chat-config-kb-check-ds_unready')).toBeDisabled();
    expect(screen.getByText('暂无文档，暂不可绑定对话')).toBeInTheDocument();
  });

  it('shows dataset-not-ready guidance instead of locked-chat guidance', async () => {
    useAuth.mockReturnValue({ user: { role: 'sub_admin' } });
    knowledgeApi.updateRagflowChat.mockRejectedValue(new Error('chat_dataset_not_ready: ds1'));

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    fireEvent.click(screen.getByTestId('chat-config-save'));

    await waitFor(() => {
      expect(screen.getByTestId('chat-config-detail-error')).toHaveTextContent(
        '所选知识库还没有已解析文档，暂时不能绑定到对话。请先上传并完成解析。'
      );
    });
    expect(screen.queryByTestId('chat-config-copy-new')).not.toBeInTheDocument();
  });

  it('keeps normal users in read-only mode', async () => {
    useAuth.mockReturnValue({ user: { role: 'viewer' } });

    render(<ChatConfigsPanel />);

    await waitFor(() => expect(screen.getByTestId('chat-config-name')).toHaveValue('Chat 1'));
    expect(screen.queryByTestId('chat-config-new')).not.toBeInTheDocument();
    expect(screen.queryByTestId('chat-config-save')).not.toBeInTheDocument();
    expect(screen.getByTestId('chat-config-name')).toBeDisabled();
  });
});
