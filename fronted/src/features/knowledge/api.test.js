import { knowledgeApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../documents/api', () => ({
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

  it('normalizes dataset and directory endpoints to stable feature contracts', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ datasets: [{ id: 'ds-1' }] })
      .mockResolvedValueOnce({ dataset: { id: 'ds-1', name: 'KB 1' } })
      .mockResolvedValueOnce({ dataset: { id: 'ds-1', name: 'KB 1 updated' } })
      .mockResolvedValueOnce({ dataset: { id: 'ds-2', name: 'KB 2' } })
      .mockResolvedValueOnce({ request: { request_id: 'req-delete-1', status: 'in_approval' } })
      .mockResolvedValueOnce({ nodes: [{ id: 'root-1' }], datasets: [{ id: 'ds-1' }] })
      .mockResolvedValueOnce({ node: { id: 'node-1', name: 'Folder 1' } })
      .mockResolvedValueOnce({ node: { id: 'node-1', name: 'Folder 1 renamed' } })
      .mockResolvedValueOnce({ result: { message: 'knowledge_directory_deleted', node_id: 'node-1' } })
      .mockResolvedValueOnce({
        result: {
          message: 'knowledge_dataset_directory_assigned',
          dataset_id: 'ds-1',
          node_id: 'node-1',
        },
      });

    await expect(knowledgeApi.listRagflowDatasets()).resolves.toEqual([{ id: 'ds-1' }]);
    await expect(knowledgeApi.getRagflowDataset('ds-1')).resolves.toEqual({
      id: 'ds-1',
      name: 'KB 1',
    });
    await expect(knowledgeApi.updateRagflowDataset('ds-1', { name: 'KB 1 updated' })).resolves.toEqual({
      id: 'ds-1',
      name: 'KB 1 updated',
    });
    await expect(knowledgeApi.createRagflowDataset({ name: 'KB 2' })).resolves.toEqual({
      id: 'ds-2',
      name: 'KB 2',
    });
    await expect(knowledgeApi.deleteRagflowDataset('ds-2')).resolves.toEqual({
      request_id: 'req-delete-1',
      status: 'in_approval',
    });
    await expect(knowledgeApi.listKnowledgeDirectories({ companyId: 7 })).resolves.toEqual({
      nodes: [{ id: 'root-1' }],
      datasets: [{ id: 'ds-1' }],
    });
    await expect(
      knowledgeApi.createKnowledgeDirectory({ name: 'Folder 1' }, { companyId: 7 })
    ).resolves.toEqual({
      id: 'node-1',
      name: 'Folder 1',
    });
    await expect(
      knowledgeApi.updateKnowledgeDirectory('node-1', { name: 'Folder 1 renamed' })
    ).resolves.toEqual({
      id: 'node-1',
      name: 'Folder 1 renamed',
    });
    await expect(knowledgeApi.deleteKnowledgeDirectory('node-1')).resolves.toEqual({
      message: 'knowledge_directory_deleted',
      node_id: 'node-1',
    });
    await expect(knowledgeApi.assignDatasetDirectory('ds-1', 'node-1')).resolves.toEqual({
      message: 'knowledge_dataset_directory_assigned',
      dataset_id: 'ds-1',
      node_id: 'node-1',
    });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/datasets',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/datasets/ds-1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/datasets/ds-1',
      {
        method: 'PUT',
        body: JSON.stringify({ name: 'KB 1 updated' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/datasets',
      {
        method: 'POST',
        body: JSON.stringify({ name: 'KB 2' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/datasets/ds-2',
      { method: 'DELETE' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      6,
      'http://auth.local/api/knowledge/directories?company_id=7',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      7,
      'http://auth.local/api/knowledge/directories?company_id=7',
      {
        method: 'POST',
        body: JSON.stringify({ name: 'Folder 1' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      8,
      'http://auth.local/api/knowledge/directories/node-1',
      {
        method: 'PUT',
        body: JSON.stringify({ name: 'Folder 1 renamed' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      9,
      'http://auth.local/api/knowledge/directories/node-1',
      { method: 'DELETE' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      10,
      'http://auth.local/api/knowledge/directories/datasets/ds-1/node',
      {
        method: 'PUT',
        body: JSON.stringify({ node_id: 'node-1' }),
      }
    );
  });

  it('fails fast when knowledge payloads do not match the backend contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ dataset: [] })
      .mockResolvedValueOnce({ dataset: null })
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ request_id: 'req-delete-1' })
      .mockResolvedValueOnce({ nodes: {}, datasets: [] })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ result: { message: 'knowledge_dataset_directory_assigned', dataset_id: '' } });

    await expect(knowledgeApi.listRagflowDatasets()).rejects.toThrow('ragflow_dataset_list_invalid_payload');
    await expect(knowledgeApi.getRagflowDataset('ds-1')).rejects.toThrow('ragflow_dataset_get_invalid_payload');
    await expect(knowledgeApi.updateRagflowDataset('ds-1', {})).rejects.toThrow(
      'ragflow_dataset_update_invalid_payload'
    );
    await expect(knowledgeApi.createRagflowDataset({})).rejects.toThrow(
      'ragflow_dataset_create_invalid_payload'
    );
    await expect(knowledgeApi.deleteRagflowDataset('ds-1')).rejects.toThrow(
      'ragflow_dataset_delete_invalid_payload'
    );
    await expect(knowledgeApi.listKnowledgeDirectories()).rejects.toThrow(
      'knowledge_directory_tree_invalid_payload'
    );
    await expect(knowledgeApi.createKnowledgeDirectory({ name: 'Folder 1' })).rejects.toThrow(
      'knowledge_directory_create_invalid_payload'
    );
    await expect(knowledgeApi.updateKnowledgeDirectory('node-1', { name: 'Folder 1' })).rejects.toThrow(
      'knowledge_directory_update_invalid_payload'
    );
    await expect(knowledgeApi.deleteKnowledgeDirectory('node-1')).rejects.toThrow(
      'knowledge_directory_delete_invalid_payload'
    );
    await expect(knowledgeApi.assignDatasetDirectory('ds-1', null)).rejects.toThrow(
      'knowledge_directory_assign_invalid_payload'
    );
  });
});
