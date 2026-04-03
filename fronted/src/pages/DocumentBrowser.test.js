import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentBrowser from './DocumentBrowser';
import useDocumentBrowserPage from '../features/knowledge/documentBrowser/useDocumentBrowserPage';

jest.mock('../features/knowledge/documentBrowser/useDocumentBrowserPage', () => jest.fn());
jest.mock('../features/knowledge/documentBrowser/components/BatchTransferProgress', () => () => null);
jest.mock('../features/knowledge/documentBrowser/components/DatasetPanel', () => () => <div data-testid="browser-dataset-panel" />);
jest.mock('../features/knowledge/documentBrowser/components/FolderTree', () => () => <div data-testid="browser-folder-tree" />);
jest.mock('../features/knowledge/documentBrowser/components/TransferDialog', () => () => null);
jest.mock('../shared/documents/preview/DocumentPreviewModal', () => ({ DocumentPreviewModal: () => null }));

const createHookState = (overrides = {}) => ({
  canDownload: () => true,
  datasetsWithFolders: [
    { id: 'ds1', name: '知识库A', node_id: 'node-1', node_path: '/A' },
    { id: 'ds2', name: '知识库B', node_id: 'node-2', node_path: '/B' },
  ],
  visibleDatasets: [
    { id: 'ds1', name: '知识库A', node_id: 'node-1', node_path: '/A' },
    { id: 'ds2', name: '知识库B', node_id: 'node-2', node_path: '/B' },
  ],
  visibleNodeIds: new Set(['node-1', 'node-2']),
  indexes: { byId: new Map(), childrenByParent: new Map() },
  currentFolderId: '',
  expandedFolderIds: [],
  folderBreadcrumb: [{ id: '', name: '根目录' }],
  datasetsInCurrentFolder: [{ id: 'ds1', name: '知识库A', node_id: 'node-1', node_path: '/A' }],
  transferTargetOptions: [],
  datasetFilterKeyword: '',
  recentDatasetKeywords: [],
  quickDatasets: [
    { id: 'ds1', name: '知识库A', node_id: 'node-1', node_path: '/A' },
    { id: 'ds2', name: '知识库B', node_id: 'node-2', node_path: '/B' },
  ],
  documents: {},
  documentErrors: {},
  loading: false,
  error: null,
  expandedDatasets: new Set(),
  actionLoading: {},
  previewOpen: false,
  previewTarget: null,
  transferDialog: null,
  batchTransferProgress: null,
  selectedCount: 0,
  totalDocs: 25,
  setDatasetFilterKeyword: jest.fn(),
  setPreviewOpen: jest.fn(),
  setPreviewTarget: jest.fn(),
  setTransferDialog: jest.fn(),
  setBatchTransferProgress: jest.fn(),
  quickDatasetStats: null,
  expandAll: jest.fn(),
  collapseAll: jest.fn(),
  refreshAll: jest.fn(),
  openQuickDataset: jest.fn(),
  toggleDataset: jest.fn(),
  fetchDocumentsForDataset: jest.fn(),
  isAllSelectedInDataset: jest.fn(() => false),
  handleSelectAllInDataset: jest.fn(),
  isDocSelected: jest.fn(() => false),
  handleSelectDoc: jest.fn(),
  handleView: jest.fn(),
  handleDownload: jest.fn(),
  handleDelete: jest.fn(),
  openSingleTransferDialog: jest.fn(),
  canDelete: () => false,
  canUpload: () => false,
  clearAllSelections: jest.fn(),
  handleBatchDownload: jest.fn(),
  openBatchTransferDialog: jest.fn(),
  handleTransferConfirm: jest.fn(),
  commitKeyword: jest.fn(),
  openFolder: jest.fn(),
  toggleFolderExpand: jest.fn(),
  ...overrides,
});

describe('DocumentBrowser', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders quick dataset slots without the removed header blocks', async () => {
    const user = userEvent.setup();
    const hookState = createHookState();
    useDocumentBrowserPage.mockReturnValue(hookState);

    render(<DocumentBrowser />);

    expect(screen.getByTestId('browser-quick-datasets')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { level: 2 })).not.toBeInTheDocument();
    expect(screen.queryByTestId('browser-expand-all')).not.toBeInTheDocument();
    expect(screen.queryByTestId('browser-collapse-all')).not.toBeInTheDocument();
    expect(screen.queryByTestId('browser-refresh-all')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('browser-quick-dataset-ds1'));
    expect(hookState.openQuickDataset).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'ds1', name: '知识库A' })
    );
  });
});
