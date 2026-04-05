import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NasBrowser from './NasBrowser';
import { knowledgeApi } from '../features/knowledge/api';
import nasApi from '../features/nas/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/knowledge/api', () => ({
  __esModule: true,
  knowledgeApi: {
    listRagflowDatasets: jest.fn(),
  },
}));

jest.mock('../features/nas/api', () => ({
  __esModule: true,
  default: {
    listFiles: jest.fn(),
    importFolder: jest.fn(),
    getFolderImportStatus: jest.fn(),
    importFile: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('NasBrowser', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      isAdmin: () => true,
    });
    knowledgeApi.listRagflowDatasets.mockResolvedValue([
      { id: 'kb-1', name: 'KB-1' },
    ]);
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

  it('loads NAS items and imports a file through the feature API', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <NasBrowser />
      </MemoryRouter>
    );

    expect(await screen.findByTestId('nas-browser-page')).toBeInTheDocument();
    expect(nasApi.listFiles).toHaveBeenCalledWith('');

    await user.click(await screen.findByTestId('nas-import-btn-docs_manual_pdf'));
    expect(await screen.findByTestId('nas-import-dialog')).toBeInTheDocument();

    await user.click(screen.getByTestId('nas-import-confirm'));

    await waitFor(() => {
      expect(nasApi.importFile).toHaveBeenCalledWith('docs/manual.pdf', 'KB-1');
    });
  });
});
