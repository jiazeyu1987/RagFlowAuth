import { useCallback, useState } from 'react';

import { resolveHistoryKey } from './downloadPageUtils';

export default function useDownloadHistoryActions({
  manager,
  localKbRef,
  msg,
  sessionId,
  selectedHistoryKey,
  setSelectedHistoryKey,
  loadHistoryKeywords,
  loadHistoryItems,
  clearHistoryPayload,
  refreshSession,
  setError,
  setInfo,
}) {
  const [deletingHistoryKey, setDeletingHistoryKey] = useState('');
  const [addingHistoryKey, setAddingHistoryKey] = useState('');

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
        if (next) {
          await loadHistoryItems(next);
        } else {
          clearHistoryPayload();
        }
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
      setError,
      setInfo,
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
      setError,
      setInfo,
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
    setError,
    setInfo,
  ]);

  return {
    deletingHistoryKey,
    addingHistoryKey,
    deleteHistoryKeyword,
    addHistoryKeywordToKb,
    refreshHistoryPanel,
  };
}
