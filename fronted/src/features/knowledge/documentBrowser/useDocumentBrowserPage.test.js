import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentBrowserPage from './useDocumentBrowserPage';
import { knowledgeApi } from '../api';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../../shared/documents/documentClient', () => ({
  __esModule: true,
  default: {
    downloadToBrowser: jest.fn(),
    delete: jest.fn(),
    batchDownloadRagflowToBrowser: jest.fn(),
  },
  DOCUMENT_SOURCE: {
    RAGFLOW: 'ragflow',
    KNOWLEDGE: 'knowledge',
  },
}));

jest.mock('../api', () => ({
  __esModule: true,
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
    listKnowledgeDirectories: jest.fn(),
    listRagflowDocuments: jest.fn(),
    transferRagflowDocument: jest.fn(),
  },
}));

const { useAuth } = jest.requireMock('../../../hooks/useAuth');

const wrapper = ({ children }) => (
  <MemoryRouter>
    {children}
  </MemoryRouter>
);

describe('useDocumentBrowserPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { user_id: 'u-1' },
      can: jest.fn((resource, action) => {
        if (resource === 'ragflow_documents' && action === 'upload') return true;
        if (resource === 'ragflow_documents' && action === 'delete') return true;
        return false;
      }),
      canDownload: jest.fn(() => true),
      accessibleKbs: ['KB-1', 'KB-2'],
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue({
      datasets: [
        { id: 'ds-1', name: 'KB-1' },
        { id: 'ds-2', name: 'KB-2' },
      ],
    });
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [],
      datasets: [],
    });
    knowledgeApi.listRagflowDocuments.mockImplementation(async (datasetName) => {
      if (datasetName === 'KB-1') {
        return [{ id: 'doc-1', name: 'Doc 1' }];
      }
      return [];
    });
    knowledgeApi.transferRagflowDocument.mockResolvedValue({ success: true });
  });

  it('loads datasets/documents and transfers through knowledgeApi', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalled();
      expect(knowledgeApi.listRagflowDocuments).toHaveBeenCalledWith('KB-1');
      expect(result.current.datasetsWithFolders).toHaveLength(2);
    });

    act(() => {
      result.current.openSingleTransferDialog('doc-1', 'KB-1', 'copy');
    });

    await waitFor(() => {
      expect(result.current.transferDialog).toEqual(
        expect.objectContaining({
          scope: 'single',
          docId: 'doc-1',
          sourceDatasetName: 'KB-1',
          operation: 'copy',
        })
      );
    });

    await act(async () => {
      await result.current.handleTransferConfirm();
    });

    expect(knowledgeApi.transferRagflowDocument).toHaveBeenCalledWith(
      'doc-1',
      'KB-1',
      'KB-2',
      'copy'
    );
  });
});
