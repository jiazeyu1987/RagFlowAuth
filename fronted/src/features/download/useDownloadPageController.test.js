import { act, renderHook } from '@testing-library/react';

import useDownloadPageController from './useDownloadPageController';
import useDownloadHistory from './useDownloadHistory';
import useDownloadSessionPolling from './useDownloadSessionPolling';

jest.mock('./useDownloadHistory', () => jest.fn());
jest.mock('./useDownloadSessionPolling', () => jest.fn());

const DEFAULT_SOURCES = { sourceA: { enabled: true, limit: 10 } };
const SOURCE_LABEL_MAP = { sourceA: 'Source A' };

describe('useDownloadPageController', () => {
  const buildManager = () => ({
    parseKeywords: jest.fn((text) => (text ? [text] : [])),
    createSession: jest.fn().mockResolvedValue({
      session: { session_id: 'session-1', status: 'running' },
      items: [],
      source_errors: {},
      source_stats: {},
      summary: { total: 0, downloaded: 0 },
    }),
    getSession: jest.fn().mockResolvedValue({
      session: { session_id: 'session-1', status: 'running' },
      items: [],
      source_errors: {},
      source_stats: {},
      summary: { total: 0, downloaded: 0 },
    }),
    stopSession: jest.fn(),
    addItemToLocalKb: jest.fn(),
    deleteItem: jest.fn(),
    addAllToLocalKb: jest.fn(),
    deleteSession: jest.fn(),
    deleteHistoryKeyword: jest.fn(),
    addHistoryToLocalKb: jest.fn(),
    toPreviewTarget: jest.fn(),
  });

  const renderController = (manager) =>
    renderHook(() =>
      useDownloadPageController({
        manager,
        storageKey: 'download-controller-test',
        localKbRef: '[local]',
        defaultSources: DEFAULT_SOURCES,
        sourceLabelMap: SOURCE_LABEL_MAP,
        normalizeHistoryKeywords: (items) => items,
      })
    );

  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    useDownloadHistory.mockReturnValue({
      historyKeywords: [],
      historyLoading: false,
      historyError: '',
      selectedHistoryKey: '',
      setSelectedHistoryKey: jest.fn(),
      historyPayload: null,
      historyItems: [],
      historyItemsLoading: false,
      loadHistoryKeywords: jest.fn().mockResolvedValue([]),
      loadHistoryItems: jest.fn().mockResolvedValue(null),
      clearHistoryPayload: jest.fn(),
    });
    useDownloadSessionPolling.mockImplementation(() => {});
  });

  it('treats already-finished stop responses as completed stop actions', async () => {
    const manager = buildManager();
    manager.stopSession.mockResolvedValue({
      message: 'paper_download_session_already_finished',
      session_id: 'session-1',
      status: 'completed',
      already_finished: true,
    });

    const { result } = renderController(manager);

    await act(async () => {
      await result.current.runDownload();
    });

    await act(async () => {
      await result.current.stopDownload();
    });

    expect(manager.stopSession).toHaveBeenCalledWith('session-1');
    expect(result.current.info).toBe('Download stopped');
    expect(result.current.error).toBe('');
  });

  it('keeps the waiting message when the worker is still stopping', async () => {
    const manager = buildManager();
    manager.stopSession.mockResolvedValue({
      message: 'paper_download_session_stop_requested',
      session_id: 'session-1',
      status: 'stopping',
      already_finished: false,
    });

    const { result } = renderController(manager);

    await act(async () => {
      await result.current.runDownload();
    });

    await act(async () => {
      await result.current.stopDownload();
    });

    expect(result.current.info).toBe('Stop requested, waiting for current item to finish.');
    expect(result.current.error).toBe('');
  });
});
