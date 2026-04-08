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
  let promptSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();
    promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('调整上传后缀');

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
      allowedExtensions: ['.txt', '.pdf'],
      updatedAtMs: 1,
    });

    knowledgeUploadApi.updateAllowedExtensions.mockResolvedValue({
      allowedExtensions: ['.txt', '.pdf'],
      updatedAtMs: 2,
    });

    knowledgeUploadApi.uploadDocument.mockResolvedValue({
      request_id: 'req-upload-1',
    });
  });

  afterEach(() => {
    promptSpy.mockRestore();
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

  it('disables upload capability when allowed extensions cannot be loaded', async () => {
    knowledgeUploadApi.getAllowedExtensions.mockRejectedValue(new Error('upload_extensions_unavailable'));

    const { result } = renderHook(() => useKnowledgeUploadPage());

    await waitFor(() => {
      expect(result.current.loadingExtensions).toBe(false);
    });

    expect(result.current.allowedExtensions).toEqual([]);
    expect(result.current.extensionsMessage).toEqual(
      expect.objectContaining({ type: 'error' })
    );

    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });
    act(() => {
      result.current.handleFileSelect({
        target: {
          files: [file],
          value: 'demo.txt',
        },
      });
    });

    expect(result.current.error).toBe('upload_extensions_unavailable');
    expect(knowledgeUploadApi.uploadDocument).not.toHaveBeenCalled();
  });

  it('saves extension configuration changes for managers', async () => {
    useAuth.mockReturnValue({
      accessibleKbs: ['KB-1', 'ds-kb-1'],
      loading: false,
      canViewKbConfig: () => true,
    });

    knowledgeUploadApi.updateAllowedExtensions.mockResolvedValue({
      allowedExtensions: ['.pdf', '.txt', '.dwg'],
      updatedAtMs: 2,
    });

    const { result } = renderHook(() => useKnowledgeUploadPage());

    await waitFor(() => {
      expect(result.current.loadingExtensions).toBe(false);
    });

    act(() => {
      result.current.setExtensionDraft('dwg');
    });

    act(() => {
      result.current.handleAddExtension();
    });

    await act(async () => {
      await result.current.handleSaveExtensions();
    });

    expect(window.prompt).toHaveBeenCalledWith('请输入本次上传后缀配置变更原因');
    expect(knowledgeUploadApi.updateAllowedExtensions).toHaveBeenCalledWith(
      ['.dwg', '.pdf', '.txt'],
      '调整上传后缀'
    );
    expect(result.current.extensionsMessage).toEqual(
      expect.objectContaining({ type: 'success' })
    );
  });

  it('clears kbId and fails fast when the user has no visible knowledge base', async () => {
    useAuth.mockReturnValue({
      accessibleKbs: [],
      loading: false,
      canViewKbConfig: () => false,
    });

    const { result } = renderHook(() => useKnowledgeUploadPage());

    await waitFor(() => {
      expect(result.current.loadingDatasets).toBe(false);
    });

    expect(result.current.kbId).toBe('');

    const file = new File(['hello'], 'demo.txt', { type: 'text/plain' });
    act(() => {
      result.current.handleFileSelect({
        target: {
          files: [file],
          value: 'demo.txt',
        },
      });
    });

    await act(async () => {
      await result.current.handleUpload({
        preventDefault() {},
      });
    });

    expect(result.current.error).toBe('missing_kb_id');
    expect(knowledgeUploadApi.uploadDocument).not.toHaveBeenCalled();
  });
});
