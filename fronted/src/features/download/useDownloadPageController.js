import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  clampLimit,
  resolveHistoryKey,
  resolveItemSessionId,
} from './downloadPageUtils';
import useDownloadHistory from './useDownloadHistory';
import useDownloadSessionPolling from './useDownloadSessionPolling';

export default function useDownloadPageController({
  manager,
  storageKey,
  localKbRef,
  defaultSources,
  sourceLabelMap,
  normalizeHistoryKeywords,
  strictCompletionValidation = false,
  messages,
}) {
  const [keywordText, setKeywordText] = useState('');
  const [useAnd, setUseAnd] = useState(true);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [sources, setSources] = useState(defaultSources);
  const [configReady, setConfigReady] = useState(false);

  const [sessionPayload, setSessionPayload] = useState(null);
  const [sourceErrors, setSourceErrors] = useState({});
  const [sourceStats, setSourceStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [addingAll, setAddingAll] = useState(false);
  const [deletingSession, setDeletingSession] = useState(false);
  const [addingItemId, setAddingItemId] = useState(null);
  const [deletingItemId, setDeletingItemId] = useState(null);

  const [resultTab, setResultTab] = useState('current');
  const [deletingHistoryKey, setDeletingHistoryKey] = useState('');
  const [addingHistoryKey, setAddingHistoryKey] = useState('');

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const baseMessages = useMemo(
    () => ({
      keywordsError: 'Failed to load history keywords',
      itemsError: 'Failed to load history items',
      startedInfo: 'Download started. Results will stream in.',
      downloadFailed: 'Download failed',
      stopDoneInfo: 'Download stopped',
      stopRequestedInfo: 'Stop requested, waiting for current item to finish.',
      stopFailed: 'Failed to stop download',
      progressFailed: 'Failed to load download progress',
      noResultsError: 'No downloadable results found for the configured sources.',
      noDownloadedError: 'Results were found, but all downloads failed. Check source errors.',
      completedInfo: (downloaded, total) => `Download completed: ${downloaded} / ${total}`,
      stoppedInfo: (downloaded, total) => `Download stopped: ${downloaded} / ${total}`,
      stoppingInfo: 'Stopping after current item...',
      taskFailed: 'Download task failed',
      addItemInfo: `Added to ${localKbRef}`,
      addItemFailed: 'Failed to add item',
      deleteItemConfirm: `Delete this result? If it was added to ${localKbRef}, that document will also be deleted.`,
      deleteItemInfo: 'Result deleted',
      deleteItemFailed: 'Failed to delete result',
      addAllInfo: (res) => `Bulk add done: success ${res?.success || 0}, failed ${res?.failed || 0}`,
      addAllFailed: 'Failed to add all results',
      deleteSessionConfirm: `Delete current download session and added docs in ${localKbRef}?`,
      deleteSessionInfo: (res) => `Deleted: items ${res?.deleted_items || 0}, docs ${res?.deleted_docs || 0}`,
      deleteSessionFailed: 'Failed to delete session',
      deleteHistoryConfirm: (row) =>
        `Delete history keyword "${row?.keyword_display || ''}" and all local files?`,
      deleteHistoryInfo: (res) =>
        `History deleted: sessions ${res?.deleted_sessions || 0}, items ${res?.deleted_items || 0}, files ${res?.deleted_files || 0}`,
      deleteHistoryFailed: 'Failed to delete history keyword',
      addHistoryInfo: (res) =>
        `History bulk add done: success ${res?.success || 0}, failed ${res?.failed || 0}`,
      addHistoryFailed: 'Failed to add history keyword to KB',
      refreshHistoryInfo: 'History refreshed',
      refreshHistoryFailed: 'Failed to refresh history',
    }),
    [localKbRef]
  );

  const msg = useMemo(
    () => ({ ...baseMessages, ...(messages || {}) }),
    [baseMessages, messages]
  );

  const parsedKeywords = useMemo(
    () => manager.parseKeywords(keywordText),
    [manager, keywordText]
  );
  const sessionId = String(sessionPayload?.session?.session_id || '');
  const sessionStatus = String(sessionPayload?.session?.status || '');
  const items = useMemo(
    () => (Array.isArray(sessionPayload?.items) ? sessionPayload.items : []),
    [sessionPayload?.items]
  );

  const {
    historyKeywords,
    historyLoading,
    historyError,
    selectedHistoryKey,
    setSelectedHistoryKey,
    historyPayload,
    historyItems,
    historyItemsLoading,
    loadHistoryKeywords,
    loadHistoryItems,
    clearHistoryPayload,
  } = useDownloadHistory({
    manager,
    normalizeHistoryKeywords,
    keywordsErrorMessage: msg.keywordsError,
    itemsErrorMessage: msg.itemsError,
  });

  const updateSource = useCallback((key, patch) => {
    setSources((previous) => ({
      ...previous,
      [key]: { ...(previous[key] || {}), ...patch },
    }));
  }, []);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (typeof parsed?.keywordText === 'string') setKeywordText(parsed.keywordText);
      if (typeof parsed?.useAnd === 'boolean') setUseAnd(parsed.useAnd);
      if (typeof parsed?.autoAnalyze === 'boolean') setAutoAnalyze(parsed.autoAnalyze);
      if (parsed?.sources && typeof parsed.sources === 'object') {
        const next = {};
        Object.keys(sourceLabelMap).forEach((key) => {
          const cfg = parsed.sources[key] || {};
          const fallback = defaultSources[key] || { enabled: false, limit: 30 };
          next[key] = {
            enabled:
              typeof cfg.enabled === 'boolean'
                ? cfg.enabled
                : Boolean(fallback.enabled),
            limit: clampLimit(cfg.limit ?? fallback.limit),
          };
        });
        setSources(next);
      }
    } catch (_) {
      // ignore invalid cache
    } finally {
      setConfigReady(true);
    }
  }, [defaultSources, sourceLabelMap, storageKey]);

  useEffect(() => {
    if (!configReady) return;
    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({ keywordText, useAnd, autoAnalyze, sources })
      );
    } catch (_) {
      // ignore storage errors
    }
  }, [autoAnalyze, configReady, keywordText, sources, storageKey, useAnd]);

  const refreshSession = useCallback(
    async (id = sessionId) => {
      if (!id) return null;
      const data = await manager.getSession(id);
      setSessionPayload(data);
      setSourceErrors(data?.source_errors || {});
      setSourceStats(data?.source_stats || {});
      return data;
    },
    [manager, sessionId]
  );

  useEffect(() => {
    loadHistoryKeywords();
  }, [loadHistoryKeywords]);

  useEffect(() => {
    if (!selectedHistoryKey) return;
    loadHistoryItems(selectedHistoryKey);
  }, [loadHistoryItems, selectedHistoryKey]);

  useDownloadSessionPolling({
    sessionId,
    sessionStatus,
    loadSession: refreshSession,
    onSessionData: (data) => {
      const status = String(data?.session?.status || '');
      const total = Number(data?.summary?.total || 0);
      const downloaded = Number(data?.summary?.downloaded || 0);

      if (status === 'completed') {
        if (strictCompletionValidation && total <= 0) {
          setError(msg.noResultsError);
          setInfo('');
          return;
        }
        if (strictCompletionValidation && downloaded <= 0) {
          setError(msg.noDownloadedError);
          setInfo('');
          return;
        }
        setError('');
        setInfo(msg.completedInfo(downloaded, total));
        return;
      }

      if (status === 'stopped') {
        setError('');
        setInfo(msg.stoppedInfo(downloaded, total));
        return;
      }

      if (status === 'stopping') {
        setInfo(msg.stoppingInfo);
        return;
      }

      if (status === 'failed') {
        setError(data?.session?.error || msg.taskFailed);
        setInfo('');
      }
    },
    onSessionError: (pollError) => {
      setError(pollError?.message || msg.progressFailed);
    },
  });

  const runDownload = useCallback(async () => {
    setLoading(true);
    setError('');
    setInfo('');
    try {
      const data = await manager.createSession({
        keywordText,
        useAnd,
        autoAnalyze,
        sources,
      });
      setSessionPayload({
        session: data?.session || null,
        items: Array.isArray(data?.items) ? data.items : [],
        summary: data?.summary || null,
      });
      setSourceErrors(data?.source_errors || {});
      setSourceStats(data?.source_stats || {});
      setResultTab('current');
      setInfo(msg.startedInfo);
      loadHistoryKeywords();
    } catch (runError) {
      setError(runError?.message || msg.downloadFailed);
      setSessionPayload(null);
      setSourceErrors({});
      setSourceStats({});
    } finally {
      setLoading(false);
    }
  }, [
    autoAnalyze,
    keywordText,
    loadHistoryKeywords,
    manager,
    msg.downloadFailed,
    msg.startedInfo,
    sources,
    useAnd,
  ]);

  const stopDownload = useCallback(async () => {
    if (!sessionId) return;
    setStopping(true);
    setError('');
    try {
      const response = await manager.stopSession(sessionId);
      setInfo(response?.already_finished || response?.status === 'stopped' ? msg.stopDoneInfo : msg.stopRequestedInfo);
      await refreshSession(sessionId);
    } catch (stopError) {
      setError(stopError?.message || msg.stopFailed);
    } finally {
      setStopping(false);
    }
  }, [
    manager,
    msg.stopDoneInfo,
    msg.stopFailed,
    msg.stopRequestedInfo,
    refreshSession,
    sessionId,
  ]);

  const openPreview = useCallback(
    (item) => {
      const sid = resolveItemSessionId(item, sessionId);
      if (!sid || !item?.item_id || !item?.has_file) return;
      const target = manager.toPreviewTarget(sid, item);
      if (!target) return;
      setPreviewTarget(target);
      setPreviewOpen(true);
    },
    [manager, sessionId]
  );

  const addOne = useCallback(
    async (item) => {
      const sid = resolveItemSessionId(item, sessionId);
      if (!sid || !item?.item_id) return;
      setAddingItemId(item.item_id);
      setError('');
      setInfo('');
      try {
        await manager.addItemToLocalKb(sid, item.item_id, localKbRef);
        if (sid === sessionId) await refreshSession(sessionId);
        await loadHistoryItems();
        setInfo(msg.addItemInfo);
      } catch (addError) {
        setError(addError?.message || msg.addItemFailed);
      } finally {
        setAddingItemId(null);
      }
    },
    [
      loadHistoryItems,
      localKbRef,
      manager,
      msg.addItemFailed,
      msg.addItemInfo,
      refreshSession,
      sessionId,
    ]
  );

  const deleteOne = useCallback(
    async (item) => {
      const sid = resolveItemSessionId(item, sessionId);
      if (!sid || !item?.item_id) return;
      if (!window.confirm(msg.deleteItemConfirm)) return;
      setDeletingItemId(item.item_id);
      setError('');
      setInfo('');
      try {
        await manager.deleteItem(sid, item.item_id, { deleteLocalKb: true });
        if (sid === sessionId) await refreshSession(sessionId);
        await loadHistoryKeywords();
        await loadHistoryItems();
        setInfo(msg.deleteItemInfo);
      } catch (deleteError) {
        setError(deleteError?.message || msg.deleteItemFailed);
      } finally {
        setDeletingItemId(null);
      }
    },
    [
      loadHistoryItems,
      loadHistoryKeywords,
      manager,
      msg.deleteItemConfirm,
      msg.deleteItemFailed,
      msg.deleteItemInfo,
      refreshSession,
      sessionId,
    ]
  );

  const addAll = useCallback(async () => {
    if (!sessionId) return;
    setAddingAll(true);
    setError('');
    setInfo('');
    try {
      const res = await manager.addAllToLocalKb(sessionId, localKbRef);
      if (res?.session) setSessionPayload(res.session);
      else await refreshSession(sessionId);
      setInfo(msg.addAllInfo(res));
    } catch (addAllError) {
      setError(addAllError?.message || msg.addAllFailed);
    } finally {
      setAddingAll(false);
    }
  }, [
    localKbRef,
    manager,
    msg,
    refreshSession,
    sessionId,
  ]);

  const removeSession = useCallback(async () => {
    if (!sessionId) return;
    if (!window.confirm(msg.deleteSessionConfirm)) return;
    setDeletingSession(true);
    setError('');
    setInfo('');
    try {
      const res = await manager.deleteSession(sessionId, { deleteLocalKb: true });
      setSessionPayload(null);
      setInfo(msg.deleteSessionInfo(res));
      await loadHistoryKeywords();
      await loadHistoryItems();
    } catch (removeError) {
      setError(removeError?.message || msg.deleteSessionFailed);
    } finally {
      setDeletingSession(false);
    }
  }, [
    loadHistoryItems,
    loadHistoryKeywords,
    manager,
    msg,
    sessionId,
  ]);

  const deleteHistoryKeyword = useCallback(
    async (row) => {
      const key = String(row?.history_key || '');
      if (!key) return;
      if (!window.confirm(msg.deleteHistoryConfirm(row))) return;

      setDeletingHistoryKey(key);
      setError('');
      setInfo('');
      try {
        const res = await manager.deleteHistoryKeyword(key);
        setInfo(msg.deleteHistoryInfo(res));
        const list = await loadHistoryKeywords();
        const next = list.length ? String(list[0].history_key || '') : '';
        setSelectedHistoryKey(next);
        if (next) await loadHistoryItems(next);
        else clearHistoryPayload();
        if (sessionId) await refreshSession(sessionId);
      } catch (deleteError) {
        setError(deleteError?.message || msg.deleteHistoryFailed);
      } finally {
        setDeletingHistoryKey('');
      }
    },
    [
      clearHistoryPayload,
      loadHistoryItems,
      loadHistoryKeywords,
      manager,
      msg,
      refreshSession,
      sessionId,
      setSelectedHistoryKey,
    ]
  );

  const addHistoryKeywordToKb = useCallback(
    async (row) => {
      const key = String(row?.history_key || '');
      if (!key) return;

      setAddingHistoryKey(key);
      setError('');
      setInfo('');
      try {
        const res = await manager.addHistoryToLocalKb(key, localKbRef);
        setInfo(msg.addHistoryInfo(res));
        await loadHistoryKeywords();
        if (selectedHistoryKey === key) await loadHistoryItems(key);
        if (sessionId) await refreshSession(sessionId);
      } catch (addError) {
        setError(addError?.message || msg.addHistoryFailed);
      } finally {
        setAddingHistoryKey('');
      }
    },
    [
      loadHistoryItems,
      loadHistoryKeywords,
      localKbRef,
      manager,
      msg,
      refreshSession,
      selectedHistoryKey,
      sessionId,
    ]
  );

  const refreshHistoryPanel = useCallback(async () => {
    setError('');
    setInfo('');
    try {
      const list = await loadHistoryKeywords();
      const active = resolveHistoryKey(list, selectedHistoryKey);
      if (active) {
        setSelectedHistoryKey(active);
        await loadHistoryItems(active);
      } else {
        clearHistoryPayload();
      }
      setInfo(msg.refreshHistoryInfo);
    } catch (refreshError) {
      setError(refreshError?.message || msg.refreshHistoryFailed);
    }
  }, [
    clearHistoryPayload,
    loadHistoryItems,
    loadHistoryKeywords,
    msg,
    selectedHistoryKey,
    setSelectedHistoryKey,
  ]);

  return {
    keywordText,
    useAnd,
    autoAnalyze,
    sources,
    sourceErrors,
    sourceStats,
    loading,
    stopping,
    addingAll,
    deletingSession,
    addingItemId,
    deletingItemId,
    resultTab,
    deletingHistoryKey,
    addingHistoryKey,
    previewOpen,
    previewTarget,
    error,
    info,
    parsedKeywords,
    sessionId,
    sessionStatus,
    items,
    historyKeywords,
    historyLoading,
    historyError,
    selectedHistoryKey,
    historyPayload,
    historyItems,
    historyItemsLoading,
    setKeywordText,
    setUseAnd,
    setAutoAnalyze,
    setResultTab,
    setPreviewOpen,
    setSelectedHistoryKey,
    updateSource,
    runDownload,
    stopDownload,
    openPreview,
    addOne,
    deleteOne,
    addAll,
    removeSession,
    deleteHistoryKeyword,
    addHistoryKeywordToKb,
    refreshHistoryPanel,
  };
}
