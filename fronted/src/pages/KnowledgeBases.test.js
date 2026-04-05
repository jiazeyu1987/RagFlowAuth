import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import KnowledgeBases from './KnowledgeBases';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../features/knowledge/api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
    listKnowledgeDirectories: jest.fn(),
    listLocalDocuments: jest.fn(),
    getRagflowDataset: jest.fn(),
    updateRagflowDataset: jest.fn(),
    assignDatasetDirectory: jest.fn(),
    createRagflowDataset: jest.fn(),
    deleteRagflowDataset: jest.fn(),
    createKnowledgeDirectory: jest.fn(),
    updateKnowledgeDirectory: jest.fn(),
    deleteKnowledgeDirectory: jest.fn(),
  },
}));

jest.mock('../features/knowledge/knowledgeBases/components/DirectoryTreeView', () => function MockDirectoryTreeView() {
  return <div data-testid="mock-directory-tree" />;
});

jest.mock('./ChatConfigsPanel', () => ({
  ChatConfigsPanel: function MockChatConfigsPanel() {
    return <div data-testid="mock-chat-configs-panel" />;
  },
}));

const dataset = {
  id: 'ds-existing',
  name: 'Existing KB',
  document_count: 0,
  chunk_count: 0,
};

describe('KnowledgeBases', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      canManageKbDirectory: () => true,
      canManageKnowledgeTree: () => true,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([dataset]);
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [],
      datasets: [{ id: 'ds-existing', name: 'Existing KB', node_id: null }],
    });
    knowledgeApi.listLocalDocuments.mockResolvedValue({ count: 0, documents: [] });
    knowledgeApi.getRagflowDataset.mockResolvedValue(dataset);
    knowledgeApi.updateRagflowDataset.mockResolvedValue(dataset);
    knowledgeApi.assignDatasetDirectory.mockResolvedValue({});
    knowledgeApi.createRagflowDataset.mockResolvedValue({ id: 'ds-created-1', name: 'Approved KB' });
    knowledgeApi.deleteRagflowDataset.mockResolvedValue({ request_id: 'req-delete-1' });
  });

  it('shows create success message', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <KnowledgeBases />
      </MemoryRouter>
    );

    await screen.findByTestId('kbs-create-kb');
    await user.click(screen.getByTestId('kbs-create-kb'));
    await screen.findByTestId('create-kb-dialog');

    await user.type(screen.getByPlaceholderText('输入知识库名称'), 'Approved KB');
    await user.click(screen.getByText('创建'));

    await waitFor(() => {
      expect(knowledgeApi.createRagflowDataset).toHaveBeenCalledWith(expect.objectContaining({ name: 'Approved KB' }));
    });
    expect(await screen.findByText('新建知识库成功')).toBeInTheDocument();
  });

  it('shows delete request submitted message', async () => {
    const user = userEvent.setup();
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <MemoryRouter>
        <KnowledgeBases />
      </MemoryRouter>
    );

    await screen.findByTestId('kbs-row-dataset-ds-existing');
    await user.click(screen.getByTestId('kbs-row-dataset-ds-existing'));
    await screen.findByText('知识库属性');
    await user.click(screen.getByText('删除知识库'));

    await waitFor(() => {
      expect(knowledgeApi.deleteRagflowDataset).toHaveBeenCalledWith('ds-existing');
    });
    expect(await screen.findByText(/删除申请已提交/)).toBeInTheDocument();

    confirmSpy.mockRestore();
  });
});
