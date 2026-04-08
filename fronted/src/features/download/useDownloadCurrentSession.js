import { useCallback, useMemo, useState } from 'react';

import { resolveItemSessionId } from './downloadPageUtils';
import useDownloadSessionPolling from './useDownloadSessionPolling';

function buildSessionPayload(data) {
  return {
    session: data?.session || null,
    items: Array.isArray(data?.items) ? data.items : [],
    summary: data?.summary || null,
  };
}

export default function useDownloadCurrentSession({
  manager,
  localKbRef,
  msg,
  keywordText,
  useAnd,
  autoAnalyze,
  sources,
  strictCompletionValidation = false,
  loadHistoryKeywords,
  loadHistoryItems,
}) {
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
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const sessionId = String(sessionPayload?.session?.session_id || '');
  const sessionStatus = String(sessionPayload?.session?.status || '');
  const items = useMemo(
    () => (Array.isArray(sessionPayload?.items) ? sessionPayload.items : []),
    [sessionPayload?.items]
  );

  const applySessionData = useCallback((data) => {
    setSessionPayload(buildSessionPayload(data));
    setSourceErrors(data?.source_errors || {});
    setSourceStats(data?.source_stats || {});
    return data;
  }, []);

  const refreshSession = useCallback(
    async (id = sessionId) => {
      if (!id) return null;
      const data = await manager.getSession(id);
      return applySessionData(data);
    },
    [applySessionData, manager, sessionId]
  );

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
      applySessionData(data);
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
    applySessionData,
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
      setInfo(
        response?.already_finished || response?.status === 'stopped'
          ? msg.stopDoneInfo
          : msg.stopRequestedInfo
      );
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
      if (res?.session) {
        setSessionPayload(res.session);
      } else {
        await refreshSession(sessionId);
      }
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

  return {
    sourceErrors,
    sourceStats,
    loading,
    stopping,
    addingAll,
    deletingSession,
    addingItemId,
    deletingItemId,
    resultTab,
    previewOpen,
    previewTarget,
    error,
    info,
    sessionId,
    sessionStatus,
    items,
    setResultTab,
    setPreviewOpen,
    setError,
    setInfo,
    refreshSession,
    runDownload,
    stopDownload,
    openPreview,
    addOne,
    deleteOne,
    addAll,
    removeSession,
  };
}
