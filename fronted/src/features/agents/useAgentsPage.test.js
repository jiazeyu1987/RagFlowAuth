import { act, renderHook, waitFor } from '@testing-library/react';
import { useAuth } from '../../hooks/useAuth';
import { DOCUMENT_SOURCE } from '../../shared/documents/constants';
import { agentsApi } from './api';
import { knowledgeApi } from '../knowledge/api';
import { documentsApi } from '../documents/api';
import { ensureTablePreviewStyles } from '../../shared/preview/tablePreviewStyles';
import { useEscapeClose } from '../../shared/hooks/useEscapeClose';
import useSearchHistory from './hooks/useSearchHistory';
import useAgentsPage from './useAgentsPage';

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('./api', () => ({
  agentsApi: {
    searchChunks: jest.fn(),
  },
}));

jest.mock('../knowledge/api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
  },
}));

jest.mock('../documents/api', () => ({
  __esModule: true,
  documentsApi: {
    downloadToBrowser: jest.fn(),
  },
}));

jest.mock('../../shared/preview/tablePreviewStyles', () => ({
  ensureTablePreviewStyles: jest.fn(),
}));

jest.mock('../../shared/hooks/useEscapeClose', () => ({
  useEscapeClose: jest.fn(),
}));

const pushHistory = jest.fn();
const clearHistory = jest.fn();
const removeHistoryItem = jest.fn();

jest.mock('./hooks/useSearchHistory', () => ({
  __esModule: true,
  default: jest.fn(),
}));

describe('useAgentsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { user_id: 'u-1', username: 'alice' },
      canDownload: () => true,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds-1', name: 'KB 1' },
      { id: 'ds-2', name: 'KB 2' },
    ]);
    agentsApi.searchChunks.mockResolvedValue({
      chunks: [{ content: 'matched chunk' }],
      total: 1,
    });
    useSearchHistory.mockReturnValue({
      history: [],
      pushHistory,
      clearHistory,
      removeHistoryItem,
    });
  });

  it('loads datasets and searches with selected dataset ids through feature APIs', async () => {
    const { result } = renderHook(() => useAgentsPage());

    await waitFor(() => {
      expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalledTimes(1);
      expect(result.current.datasets.map((item) => item.id)).toEqual(['ds-1', 'ds-2']);
      expect(result.current.selectedDatasetIds).toEqual(['ds-1', 'ds-2']);
    });
    expect(ensureTablePreviewStyles).toHaveBeenCalledTimes(1);
    expect(useEscapeClose).toHaveBeenCalled();

    act(() => {
      result.current.setSearchQuery('capsule');
    });

    await act(async () => {
      result.current.executeSearch();
    });

    await waitFor(() => {
      expect(agentsApi.searchChunks).toHaveBeenCalledWith(
        expect.objectContaining({
          question: 'capsule',
          dataset_ids: ['ds-1', 'ds-2'],
          page: 1,
          page_size: 30,
          top_k: 30,
        })
      );
    });

    expect(pushHistory).toHaveBeenCalledWith('capsule');
    expect(result.current.searchResults).toEqual(
      expect.objectContaining({
        total: 1,
      })
    );
  });

  it('uses dataset names when downloading and previewing ragflow documents', async () => {
    const { result } = renderHook(() => useAgentsPage());

    await waitFor(() => {
      expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalledTimes(1);
      expect(result.current.datasets.map((item) => item.id)).toEqual(['ds-1', 'ds-2']);
    });

    await act(async () => {
      await result.current.handleDownloadDocument('doc-1', 'Doc.pdf', 'ds-1');
    });

    expect(documentsApi.downloadToBrowser).toHaveBeenCalledWith({
      source: DOCUMENT_SOURCE.RAGFLOW,
      docId: 'doc-1',
      datasetName: 'KB 1',
      filename: 'Doc.pdf',
    });

    await act(async () => {
      await result.current.handlePreviewDocument('doc-2', 'Preview.docx', 'ds-2');
    });

    expect(result.current.previewOpen).toBe(true);
    expect(result.current.previewTarget).toEqual({
      source: DOCUMENT_SOURCE.RAGFLOW,
      docId: 'doc-2',
      datasetName: 'KB 2',
      filename: 'Preview.docx',
    });
  });
});
