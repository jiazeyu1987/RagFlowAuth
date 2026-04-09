import { act, renderHook, waitFor } from '@testing-library/react';

import { useAuth } from '../../../hooks/useAuth';
import { knowledgeApi } from '../api';
import useKnowledgeBasesPage from './useKnowledgeBasesPage';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../api', () => ({
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

const dataset = {
  id: 'ds-existing',
  name: 'Existing KB',
  description: 'copied description',
  document_count: 0,
  chunk_count: 0,
};

describe('useKnowledgeBasesPage', () => {
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
    knowledgeApi.createRagflowDataset.mockResolvedValue({
      id: 'ds-created-1',
      name: 'Approved KB',
    });
    knowledgeApi.deleteRagflowDataset.mockResolvedValue({ request_id: 'req-delete-1' });
  });

  it('creates a knowledge base with copied dataset settings', async () => {
    const { result } = renderHook(() => useKnowledgeBasesPage());

    await waitFor(() => {
      expect(result.current.kbList).toHaveLength(1);
    });

    act(() => {
      result.current.openCreateKb();
      result.current.setCreateName('Approved KB');
    });

    await act(async () => {
      await result.current.handleCreateFromIdChange('ds-existing');
    });

    await act(async () => {
      await result.current.createKb();
    });

    expect(knowledgeApi.createRagflowDataset).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Approved KB',
        description: 'copied description',
      })
    );
    expect(result.current.kbSaveStatus).toBe('新建知识库成功');
  });

  it('loads dataset detail and submits delete request for empty knowledge bases', async () => {
    const { result } = renderHook(() => useKnowledgeBasesPage());
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

    await waitFor(() => {
      expect(result.current.filteredRows).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ id: 'ds-existing', kind: 'dataset' }),
        ])
      );
    });

    act(() => {
      result.current.handleSelectRow({ kind: 'dataset', id: 'ds-existing' });
    });

    await waitFor(() => {
      expect(result.current.selectedKb?.id).toBe('ds-existing');
    });

    await act(async () => {
      await result.current.handleDeleteSelectedKb();
    });

    expect(knowledgeApi.deleteRagflowDataset).toHaveBeenCalledWith('ds-existing');
    expect(result.current.kbSaveStatus).toBe('删除申请已提交：req-delete-1');

    confirmSpy.mockRestore();
  });

  it('uses managed root node as mount target for sub admins when creating knowledge bases', async () => {
    useAuth.mockReturnValue({
      canManageKbDirectory: () => true,
      canManageKnowledgeTree: () => true,
      isSubAdmin: () => true,
      managedKbRootNodeId: 'node-subadmin-root',
      managedKbRootPath: '/managed',
    });
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [{ id: 'node-subadmin-root', name: 'Managed', path: '/managed' }],
      datasets: [{ id: 'ds-existing', name: 'Existing KB', node_id: 'node-subadmin-root' }],
    });

    const { result } = renderHook(() => useKnowledgeBasesPage());

    await waitFor(() => {
      expect(result.current.dirOptions).toEqual(
        expect.arrayContaining([expect.objectContaining({ id: 'node-subadmin-root' })])
      );
    });
    expect(result.current.dirOptions.find((option) => option.id === '')).toBeUndefined();

    act(() => {
      result.current.openCreateKb();
      result.current.setCreateName('SubAdmin KB');
    });
    expect(result.current.createDirId).toBe('node-subadmin-root');

    await act(async () => {
      await result.current.createKb();
    });

    expect(knowledgeApi.createRagflowDataset).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'SubAdmin KB',
        node_id: 'node-subadmin-root',
      })
    );
  });
});
