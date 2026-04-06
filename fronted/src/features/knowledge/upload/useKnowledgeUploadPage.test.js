import { act, renderHook, waitFor } from '@testing-library/react';

import { useAuth } from '../../../hooks/useAuth';
import { knowledgeApi } from '../api';
import { knowledgeUploadApi } from './api';
import useKnowledgeUploadPage from './useKnowledgeUploadPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../api', () => ({
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
    listKnowledgeDirectories: jest.fn(),
  },
}));

jest.mock('./api', () => ({
  knowledgeUploadApi: {
    getAllowedExtensions: jest.fn(),
    updateAllowedExtensions: jest.fn(),
    uploadDocument: jest.fn(),
  },
}));

describe('useKnowledgeUploadPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();

    useAuth.mockReturnValue({
      accessibleKbs: ['KB-1', 'ds-kb-1'],
      loading: false,
      canViewKbConfig: () => false,
    });

    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'ds-kb-1', name: 'KB-1' },
      { id: 'ds-kb-2', name: 'KB-2' },
    ]);

    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [],
      datasets: [
        { id: 'ds-kb-1', name: 'KB-1', node_path: '/研发' },
        { id: 'ds-kb-2', name: 'KB-2', node_path: '/归档' },
      ],
    });

    knowledgeUploadApi.getAllowedExtensions.mockResolvedValue({
      allowed_extensions: ['.txt', '.pdf'],
    });

    knowledgeUploadApi.updateAllowedExtensions.mockResolvedValue({
      allowed_extensions: ['.txt', '.pdf'],
    });

    knowledgeUploadApi.uploadDocument.mockResolvedValue({
      request_id: 'req-upload-1',
    });
  });

  it('keeps only knowledge bases visible to the current user', async () => {
    const { result } = renderHook(() => useKnowledgeUploadPage());

    await waitFor(() => {
      expect(result.current.loadingDatasets).toBe(false);
    });

    expect(result.current.datasetOptions).toEqual([
      expect.objectContaining({
        key: 'ds-kb-1',
        value: 'KB-1',
      }),
    ]);
    expect(result.current.datasetOptions[0]?.label).toContain('KB-1');
    expect(result.current.kbId).toBe('KB-1');
  });

  it('uploads selected files through the knowledge upload feature api', async () => {
    const { result, unmount } = renderHook(() => useKnowledgeUploadPage());

    await waitFor(() => {
      expect(result.current.loadingDatasets).toBe(false);
    });

    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });

    act(() => {
      result.current.handleFileSelect({
        target: {
          files: [file],
          value: 'demo.txt',
        },
      });
    });

    expect(result.current.selectedFiles).toHaveLength(1);

    await act(async () => {
      await result.current.handleUpload({
        preventDefault() {},
      });
    });

    expect(knowledgeUploadApi.uploadDocument).toHaveBeenCalledWith(file, 'KB-1');
    expect(result.current.success).toContain('req-upload-1');
    expect(result.current.selectedFiles).toHaveLength(0);

    unmount();
  });
});
