import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentBrowserPage from './useDocumentBrowserPage';
import { documentBrowserApi } from './api';
import { knowledgeApi } from '../api';
import { documentsApi } from '../../documents/api';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../documents/api', () => ({
  __esModule: true,
  documentsApi: {
    downloadToBrowser: jest.fn(),
    deleteDocument: jest.fn(),
    batchDownloadRagflowToBrowser: jest.fn(),
  },
  DOCUMENT_SOURCE: {
    RAGFLOW: 'ragflow',
    KNOWLEDGE: 'knowledge',
  },
}));

jest.mock('./api', () => ({
  __esModule: true,
  documentBrowserApi: {
    listDocuments: jest.fn(),
    transferDocument: jest.fn(),
  },
}));

jest.mock('../api', () => ({
  __esModule: true,
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
    listKnowledgeDirectories: jest.fn(),
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
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds-1', name: 'KB-1' },
      { id: 'ds-2', name: 'KB-2' },
    ]);
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [],
      datasets: [],
    });
    documentBrowserApi.listDocuments.mockImplementation(async (datasetName) => {
      if (datasetName === 'KB-1') {
        return [{ id: 'doc-1', name: 'Doc 1' }];
      }
      return [];
    });
    documentBrowserApi.transferDocument.mockResolvedValue({ success: true });
  });

  it('loads datasets/documents and transfers through the document browser API', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalled();
      expect(documentBrowserApi.listDocuments).toHaveBeenCalledWith('KB-1');
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

    expect(documentBrowserApi.transferDocument).toHaveBeenCalledWith(
      'doc-1',
      'KB-1',
      'KB-2',
      'copy'
    );
  });

  it('routes batch downloads through the documents feature API', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(documentBrowserApi.listDocuments).toHaveBeenCalledWith('KB-1');
    });

    act(() => {
      result.current.handleSelectDoc('doc-1', 'KB-1');
    });

    await act(async () => {
      await result.current.handleBatchDownload();
    });

    expect(documentsApi.batchDownloadRagflowToBrowser).toHaveBeenCalledWith([
      { doc_id: 'doc-1', dataset: 'KB-1', name: 'Doc 1' },
    ]);
  });
});
