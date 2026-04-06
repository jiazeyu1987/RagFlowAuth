import { act, renderHook, waitFor } from '@testing-library/react';
import { knowledgeApi } from '../api';
import nasApi from '../../nas/api';
import { useAuth } from '../../../hooks/useAuth';
import useNasBrowserPage from './useNasBrowserPage';
import { ACTIVE_FOLDER_IMPORT_KEY } from './utils';

jest.mock('../api', () => ({
  __esModule: true,
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
  },
}));

jest.mock('../../nas/api', () => ({
  __esModule: true,
  default: {
    listFiles: jest.fn(),
    importFolder: jest.fn(),
    getFolderImportStatus: jest.fn(),
    importFile: jest.fn(),
  },
}));

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('useNasBrowserPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.removeItem(ACTIVE_FOLDER_IMPORT_KEY);
    useAuth.mockReturnValue({
      isAdmin: () => true,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([{ id: 'kb-1', name: 'KB-1' }]);
    nasApi.listFiles.mockResolvedValue({
      current_path: '',
      parent_path: null,
      items: [
        {
          name: 'manual.pdf',
          path: 'docs/manual.pdf',
          is_dir: false,
          size: 512,
          modified_at: 1712203200000,
        },
      ],
    });
    nasApi.importFile.mockResolvedValue({
      imported_count: 1,
      skipped_count: 0,
      failed_count: 0,
    });
    jest.spyOn(window, 'alert').mockImplementation(() => {});
  });

  afterEach(() => {
    window.alert.mockRestore();
  });

  it('loads the initial NAS path and datasets into stable hook state', async () => {
    const { result } = renderHook(() => useNasBrowserPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(nasApi.listFiles).toHaveBeenCalledWith('');
    expect(knowledgeApi.listRagflowDatasets).toHaveBeenCalledTimes(1);
    expect(result.current.items).toHaveLength(1);
    expect(result.current.selectedKb).toBe('KB-1');
    expect(result.current.admin).toBe(true);
  });

  it('imports a selected NAS file through the feature api using the active dataset', async () => {
    const { result } = renderHook(() => useNasBrowserPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.openImportDialog(result.current.items[0]);
    });

    expect(result.current.importDialogOpen).toBe(true);

    await act(async () => {
      await result.current.handleImport();
    });

    await waitFor(() => {
      expect(nasApi.importFile).toHaveBeenCalledWith('docs/manual.pdf', 'KB-1');
    });
    expect(result.current.importDialogOpen).toBe(false);
    expect(window.alert).toHaveBeenCalledTimes(1);
  });
});
