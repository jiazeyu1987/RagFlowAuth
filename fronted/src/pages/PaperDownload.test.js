import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import PaperDownload from './PaperDownload';
import usePaperDownloadPage from '../features/paperDownload/usePaperDownloadPage';

jest.mock('../features/paperDownload/usePaperDownloadPage', () => ({
  __esModule: true,
  default: jest.fn(),
  isSessionActive: jest.fn(() => false),
}));

jest.mock('../features/download/components/DownloadConfigCards', () => ({
  DownloadKeywordConfigCard: function MockDownloadKeywordConfigCard(props) {
    return <div data-testid="mock-paper-keywords">{props.title}</div>;
  },
  DownloadSourceConfigCard: function MockDownloadSourceConfigCard(props) {
    return <div data-testid="mock-paper-sources">{props.title}{props.children}</div>;
  },
}));

jest.mock('../features/download/components/DownloadResultToolbar', () => function MockToolbar() {
  return <div data-testid="mock-paper-toolbar" />;
});

jest.mock('../features/download/components/DownloadHistorySidebar', () => function MockSidebar() {
  return <div data-testid="mock-paper-history-sidebar" />;
});

jest.mock('../features/download/components/DownloadHistoryDetailPanel', () => function MockDetailPanel(props) {
  return <div data-testid="mock-paper-history-detail">{props.children}</div>;
});

jest.mock('../features/paperDownload/components/PaperResultList', () => function MockPaperResultList() {
  return <div data-testid="mock-paper-result-list" />;
});

jest.mock('../features/paperDownload/components/PaperSourceSummaryPanel', () => function MockPaperSourceSummaryPanel() {
  return <div data-testid="mock-paper-summary" />;
});

jest.mock('../shared/documents/preview/DocumentPreviewModal', () => ({
  DocumentPreviewModal: function MockDocumentPreviewModal(props) {
    return props.open ? <div data-testid="mock-paper-preview-modal" /> : null;
  },
}));

const createPageState = (overrides = {}) => ({
  isMobile: false,
  canDownloadFiles: true,
  handleBackToTools: jest.fn(),
  keywordText: '',
  useAnd: false,
  autoAnalyze: false,
  sources: {},
  sourceErrors: {},
  sourceStats: {},
  loading: false,
  stopping: false,
  addingAll: false,
  deletingSession: false,
  addingItemId: '',
  deletingItemId: '',
  resultTab: 'current',
  deletingHistoryKey: '',
  addingHistoryKey: '',
  previewOpen: false,
  previewTarget: null,
  error: '',
  info: '',
  parsedKeywords: [],
  sessionId: '',
  sessionStatus: 'idle',
  items: [],
  historyKeywords: [],
  historyLoading: false,
  historyError: '',
  selectedHistoryKey: '',
  historyPayload: null,
  historyItems: [],
  historyItemsLoading: false,
  setKeywordText: jest.fn(),
  setUseAnd: jest.fn(),
  setAutoAnalyze: jest.fn(),
  setResultTab: jest.fn(),
  setPreviewOpen: jest.fn(),
  setSelectedHistoryKey: jest.fn(),
  updateSource: jest.fn(),
  runDownload: jest.fn(),
  stopDownload: jest.fn(),
  openPreview: jest.fn(),
  addOne: jest.fn(),
  deleteOne: jest.fn(),
  addAll: jest.fn(),
  removeSession: jest.fn(),
  deleteHistoryKeyword: jest.fn(),
  addHistoryKeywordToKb: jest.fn(),
  refreshHistoryPanel: jest.fn(),
  ...overrides,
});

describe('PaperDownload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usePaperDownloadPage.mockReturnValue(createPageState());
  });

  it('calls the page hook back action when clicking the back button', async () => {
    const user = userEvent.setup();
    const handleBackToTools = jest.fn();
    usePaperDownloadPage.mockReturnValue(createPageState({ handleBackToTools }));

    render(<PaperDownload />);

    await user.click(screen.getByTestId('paper-download-back'));

    expect(handleBackToTools).toHaveBeenCalled();
  });

  it('passes preview open state to the preview modal', () => {
    usePaperDownloadPage.mockReturnValue(
      createPageState({
        previewOpen: true,
        previewTarget: { id: 'doc-1' },
      })
    );

    render(<PaperDownload />);

    expect(screen.getByTestId('mock-paper-preview-modal')).toBeInTheDocument();
  });
});
