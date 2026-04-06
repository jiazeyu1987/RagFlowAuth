import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import PatentDownload from './PatentDownload';
import usePatentDownloadPage from '../features/patentDownload/usePatentDownloadPage';

jest.mock('../features/patentDownload/usePatentDownloadPage', () => ({
  __esModule: true,
  default: jest.fn(),
  isSessionActive: jest.fn(() => false),
}));

jest.mock('../features/download/components/DownloadConfigCards', () => ({
  DownloadKeywordConfigCard: function MockDownloadKeywordConfigCard(props) {
    return <div data-testid="mock-patent-keywords">{props.title}</div>;
  },
  DownloadSourceConfigCard: function MockDownloadSourceConfigCard(props) {
    return <div data-testid="mock-patent-sources">{props.title}{props.children}</div>;
  },
}));

jest.mock('../features/download/components/DownloadResultToolbar', () => function MockToolbar() {
  return <div data-testid="mock-patent-toolbar" />;
});

jest.mock('../features/download/components/DownloadHistorySidebar', () => function MockSidebar() {
  return <div data-testid="mock-patent-history-sidebar" />;
});

jest.mock('../features/download/components/DownloadHistoryDetailPanel', () => function MockDetailPanel(props) {
  return <div data-testid="mock-patent-history-detail">{props.children}</div>;
});

jest.mock('../features/patentDownload/components/PatentResultList', () => function MockPatentResultList() {
  return <div data-testid="mock-patent-result-list" />;
});

jest.mock('../features/patentDownload/components/PatentSourceSummaryPanel', () => function MockPatentSourceSummaryPanel() {
  return <div data-testid="mock-patent-summary" />;
});

jest.mock('../shared/documents/preview/DocumentPreviewModal', () => ({
  DocumentPreviewModal: function MockDocumentPreviewModal(props) {
    return props.open ? <div data-testid="mock-patent-preview-modal" /> : null;
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
  sourceStats: {},
  loading: false,
  stopping: false,
  addingAll: false,
  deletingSession: false,
  error: '',
  info: '',
  resultTab: 'current',
  sessionId: '',
  sessionStatus: 'idle',
  items: [],
  parsedKeywords: [],
  frontendLogs: [],
  addingItemId: '',
  deletingItemId: '',
  previewOpen: false,
  previewTarget: null,
  historyKeywords: [],
  historyLoading: false,
  historyError: '',
  selectedHistoryKey: '',
  historyPayload: null,
  historyItems: [],
  historyItemsLoading: false,
  deletingHistoryKey: '',
  addingHistoryKey: '',
  setKeywordText: jest.fn(),
  setUseAnd: jest.fn(),
  setAutoAnalyze: jest.fn(),
  setResultTab: jest.fn(),
  setPreviewOpen: jest.fn(),
  setSelectedHistoryKey: jest.fn(),
  updateSource: jest.fn(),
  runDownload: jest.fn(),
  stopDownload: jest.fn(),
  addAll: jest.fn(),
  removeSession: jest.fn(),
  addOne: jest.fn(),
  deleteOne: jest.fn(),
  openPreview: jest.fn(),
  deleteHistoryKeyword: jest.fn(),
  addHistoryKeywordToKb: jest.fn(),
  refreshHistoryPanel: jest.fn(),
  ...overrides,
});

describe('PatentDownload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    usePatentDownloadPage.mockReturnValue(createPageState());
  });

  it('calls the page hook back action when clicking the back button', async () => {
    const user = userEvent.setup();
    const handleBackToTools = jest.fn();
    usePatentDownloadPage.mockReturnValue(createPageState({ handleBackToTools }));

    render(<PatentDownload />);

    await user.click(screen.getByTestId('patent-download-back'));

    expect(handleBackToTools).toHaveBeenCalled();
  });

  it('passes preview open state to the preview modal', () => {
    usePatentDownloadPage.mockReturnValue(
      createPageState({
        previewOpen: true,
        previewTarget: { id: 'doc-1' },
      })
    );

    render(<PatentDownload />);

    expect(screen.getByTestId('mock-patent-preview-modal')).toBeInTheDocument();
  });
});
