import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  clampLimit,
  resolveHistoryKey,
  resolveItemSessionId,
} from './downloadPageUtils';
import useDownloadHistory from './useDownloadHistory';
import useDownloadSessionPolling from './useDownloadSessionPolling';

function normalizeDisplayError(message, fallback) {
  const text = String(message || '').trim();
  if (!text) return fallback;
  return /[\u4e00-\u9fff]/.test(text) ? text : fallback;
}

function normalizeErrorMap(errorMap) {
  if (!errorMap || typeof errorMap !== 'object') return {};
  return Object.fromEntries(
    Object.entries(errorMap).map(([key, value]) => [key, normalizeDisplayError(value, '处理失败')])
  );
}

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
      keywordsError: '加载历史关键词失败',
      itemsError: '加载历史条目失败',
      startedInfo: '下载已启动，结果将持续更新。',
      downloadFailed: '下载失败',
      stopDoneInfo: '下载已停止',
      stopRequestedInfo: '已请求停止，正在等待当前条目处理完成。',
      stopFailed: '停止下载失败',
      progressFailed: '加载下载进度失败',
      noResultsError: '已配置的来源中没有可下载结果。',
      noDownloadedError: '已找到结果，但全部下载失败，请检查来源错误。',
      completedInfo: (downloaded, total) => `下载完成：${downloaded} / ${total}`,
      stoppedInfo: (downloaded, total) => `下载已停止：${downloaded} / ${total}`,
      stoppingInfo: '将在当前条目处理后停止...',
      taskFailed: '下载任务失败',
      addItemInfo: `已加入 ${localKbRef}`,
      addItemFailed: '加入条目失败',
      deleteItemConfirm: `确定删除该结果吗？若该结果已加入 ${localKbRef}，对应文档也会被删除。`,
      deleteItemInfo: '结果已删除',
      deleteItemFailed: '删除结果失败',
      addAllInfo: (res) => `批量加入完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`,
      addAllFailed: '批量加入失败',
      deleteSessionConfirm: `确定删除当前下载会话及 ${localKbRef} 中已加入的文档吗？`,
      deleteSessionInfo: (res) => `已删除：条目 ${res?.deleted_items || 0}，文档 ${res?.deleted_docs || 0}`,
      deleteSessionFailed: '删除会话失败',
      deleteHistoryConfirm: (row) =>
        `确定删除历史关键词“${row?.keyword_display || ''}”及全部本地文件吗？`,
      deleteHistoryInfo: (res) =>
        `历史记录已删除：会话 ${res?.deleted_sessions || 0}，条目 ${res?.deleted_items || 0}，文件 ${res?.deleted_files || 0}`,
      deleteHistoryFailed: '删除历史关键词失败',
      addHistoryInfo: (res) =>
        `历史批量加入完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`,
      addHistoryFailed: '将历史关键词加入知识库失败',
      refreshHistoryInfo: '历史记录已刷新',
      refreshHistoryFailed: '刷新历史记录失败',
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
      setSourceErrors(normalizeErrorMap(data?.source_errors));
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
        setError(normalizeDisplayError(data?.session?.error, msg.taskFailed));
        setInfo('');
      }
    },
    onSessionError: (pollError) => {
      setError(normalizeDisplayError(pollError?.message, msg.progressFailed));
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
      setError(normalizeDisplayError(runError?.message, msg.downloadFailed));
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
      setInfo(response?.status === 'stopped' ? msg.stopDoneInfo : msg.stopRequestedInfo);
      await refreshSession(sessionId);
    } catch (stopError) {
      setError(normalizeDisplayError(stopError?.message, msg.stopFailed));
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
        setError(normalizeDisplayError(addError?.message, msg.addItemFailed));
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
        setError(normalizeDisplayError(deleteError?.message, msg.deleteItemFailed));
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
      setError(normalizeDisplayError(addAllError?.message, msg.addAllFailed));
    } finally {
      setAddingAll(false);
    }
  }, [localKbRef, manager, msg, refreshSession, sessionId]);

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
      setError(normalizeDisplayError(removeError?.message, msg.deleteSessionFailed));
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
        setError(normalizeDisplayError(deleteError?.message, msg.deleteHistoryFailed));
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
        setError(normalizeDisplayError(addError?.message, msg.addHistoryFailed));
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
      setError(normalizeDisplayError(refreshError?.message, msg.refreshHistoryFailed));
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