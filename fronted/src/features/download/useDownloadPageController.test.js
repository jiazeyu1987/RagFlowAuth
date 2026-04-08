import { act, renderHook, waitFor } from '@testing-library/react';

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
    expect(result.current.info).toBe('下载已停止');
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

    expect(result.current.info).toBe('已请求停止，等待当前条目处理完成。');
    expect(result.current.error).toBe('');
  });

  it('hydrates persisted controller config from localStorage', async () => {
    window.localStorage.setItem(
      'download-controller-test',
      JSON.stringify({
        keywordText: 'saved keyword',
        useAnd: false,
        autoAnalyze: true,
        sources: {
          sourceA: { enabled: false, limit: 24 },
        },
      })
    );

    const { result } = renderController(buildManager());

    await waitFor(() => {
      expect(result.current.keywordText).toBe('saved keyword');
      expect(result.current.useAnd).toBe(false);
      expect(result.current.autoAnalyze).toBe(true);
      expect(result.current.sources).toEqual({
        sourceA: { enabled: false, limit: 24 },
      });
    });
  });

  it('refreshes history selection after deleting a history keyword', async () => {
    const manager = buildManager();
    manager.deleteHistoryKeyword.mockResolvedValue({
      deleted_sessions: 1,
      deleted_items: 2,
      deleted_files: 3,
    });

    const setSelectedHistoryKey = jest.fn();
    const loadHistoryKeywords = jest.fn().mockResolvedValue([
      { history_key: 'next-key', keyword_display: 'Next' },
    ]);
    const loadHistoryItems = jest.fn().mockResolvedValue(null);

    useDownloadHistory.mockReturnValue({
      historyKeywords: [],
      historyLoading: false,
      historyError: '',
      selectedHistoryKey: 'old-key',
      setSelectedHistoryKey,
      historyPayload: null,
      historyItems: [],
      historyItemsLoading: false,
      loadHistoryKeywords,
      loadHistoryItems,
      clearHistoryPayload: jest.fn(),
    });

    window.confirm = jest.fn(() => true);

    const { result } = renderController(manager);

    await act(async () => {
      await result.current.runDownload();
    });

    await act(async () => {
      await result.current.deleteHistoryKeyword({
        history_key: 'old-key',
        keyword_display: 'Old',
      });
    });

    expect(manager.deleteHistoryKeyword).toHaveBeenCalledWith('old-key');
    expect(setSelectedHistoryKey).toHaveBeenCalledWith('next-key');
    expect(loadHistoryItems).toHaveBeenCalledWith('next-key');
    expect(manager.getSession).toHaveBeenCalledWith('session-1');
  });
});
