import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { act, renderHook, waitFor } from '@testing-library/react';
import useDocumentBrowserPage from './useDocumentBrowserPage';
import { documentBrowserApi } from './api';
import { knowledgeApi } from '../api';
import { documentsApi } from '../../documents/api';
import { DOCUMENT_SOURCE } from '../../../shared/documents/constants';

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
}));

jest.mock('./api', () => ({
  __esModule: true,
  documentBrowserApi: {
    listDocuments: jest.fn(),
    deleteDocument: jest.fn(),
    transferDocument: jest.fn(),
    transferDocumentsBatch: jest.fn(),
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
    window.localStorage.clear();
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
    documentBrowserApi.deleteDocument.mockResolvedValue({ message: 'document_deleted' });
    documentBrowserApi.transferDocument.mockResolvedValue({ success: true });
    documentBrowserApi.transferDocumentsBatch.mockResolvedValue({
      ok: true,
      operation: 'copy',
      total: 1,
      successCount: 1,
      failedCount: 0,
      results: [
        {
          ok: true,
          operation: 'copy',
          sourceDatasetName: 'KB-1',
          targetDatasetName: 'KB-2',
          sourceDocId: 'doc-1',
          targetDocId: 'doc-target-1',
          filename: 'Doc 1',
          sourceDeleted: false,
          parseTriggered: true,
          parseError: '',
        },
      ],
      failed: [],
    });
    window.alert = jest.fn();
    window.confirm = jest.fn(() => true);
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

  it('routes ragflow deletes through the document browser feature API', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(documentBrowserApi.listDocuments).toHaveBeenCalledWith('KB-1');
    });

    await act(async () => {
      await result.current.handleDelete('doc-1', 'KB-1');
    });

    expect(window.confirm).toHaveBeenCalled();
    expect(documentBrowserApi.deleteDocument).toHaveBeenCalledWith('doc-1', 'KB-1');
    expect(documentsApi.deleteDocument).not.toHaveBeenCalled();
    expect(result.current.documents['KB-1']).toEqual([]);
  });

  it('routes batch transfers through the document browser batch API', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(documentBrowserApi.listDocuments).toHaveBeenCalledWith('KB-1');
    });

    act(() => {
      result.current.handleSelectDoc('doc-1', 'KB-1');
      result.current.openBatchTransferDialog('copy');
    });

    await waitFor(() => {
      expect(result.current.transferDialog).toEqual(
        expect.objectContaining({
          scope: 'batch',
          operation: 'copy',
          targetDatasetName: 'KB-1',
        })
      );
    });

    act(() => {
      result.current.setTransferDialog((previous) => ({
        ...previous,
        targetDatasetName: 'KB-2',
      }));
    });

    await act(async () => {
      await result.current.handleTransferConfirm();
    });

    expect(documentBrowserApi.transferDocumentsBatch).toHaveBeenCalledWith(
      [{ docId: 'doc-1', sourceDatasetName: 'KB-1', targetDatasetName: 'KB-2' }],
      'copy'
    );
    expect(result.current.batchTransferProgress).toEqual(
      expect.objectContaining({
        operation: 'copy',
        total: 1,
        processed: 1,
        success: 1,
        failed: 0,
        done: true,
      })
    );
  });

  it('loads and persists recent keywords and dataset usage through local storage', async () => {
    window.localStorage.setItem(
      'ragflowauth_recent_dataset_keywords_v1:u-1',
      JSON.stringify(['Alpha', 'Beta'])
    );
    window.localStorage.setItem(
      'ragflowauth_browser_dataset_usage_v1:u-1',
      JSON.stringify({ 'KB-2': 3, 'KB-1': 1 })
    );

    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(result.current.quickDatasets.map((item) => item.name)).toEqual(['KB-2', 'KB-1']);
      expect(result.current.recentDatasetKeywords).toEqual(['Alpha', 'Beta']);
    });

    act(() => {
      result.current.commitKeyword('alpha');
      result.current.openQuickDataset('KB-1');
    });

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem('ragflowauth_recent_dataset_keywords_v1:u-1'))).toEqual([
        'alpha',
        'Beta',
      ]);
      expect(JSON.parse(window.localStorage.getItem('ragflowauth_browser_dataset_usage_v1:u-1'))).toEqual({
        'KB-2': 3,
        'KB-1': 2,
      });
    });
  });

  it('opens quick datasets and preview state through the page action helpers without changing the hook contract', async () => {
    const { result } = renderHook(() => useDocumentBrowserPage(), { wrapper });

    await waitFor(() => {
      expect(documentBrowserApi.listDocuments).toHaveBeenCalledWith('KB-1');
    });

    act(() => {
      result.current.openQuickDataset('KB-1');
      result.current.handleView('doc-1', 'KB-1');
    });

    expect(result.current.expandedDatasets.has('KB-1')).toBe(true);
    expect(result.current.previewOpen).toBe(true);
    expect(result.current.previewTarget).toEqual({
      source: DOCUMENT_SOURCE.RAGFLOW,
      docId: 'doc-1',
      datasetName: 'KB-1',
      filename: 'Doc 1',
    });
  });
});
