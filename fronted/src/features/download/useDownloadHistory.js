import { useCallback, useMemo, useState } from 'react';
import { resolveHistoryKey } from './downloadPageUtils';

export default function useDownloadHistory({
  manager,
  normalizeHistoryKeywords,
  keywordsErrorMessage = '获取历史关键词失败',
  itemsErrorMessage = '获取历史记录失败',
}) {
  const [historyKeywords, setHistoryKeywords] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [selectedHistoryKey, setSelectedHistoryKey] = useState('');
  const [historyPayload, setHistoryPayload] = useState(null);
  const [historyItemsLoading, setHistoryItemsLoading] = useState(false);

  const historyItems = useMemo(
    () => (Array.isArray(historyPayload?.items) ? historyPayload.items : []),
    [historyPayload?.items]
  );

  const loadHistoryKeywords = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const res = await manager.listHistoryKeywords();
      const rawList = Array.isArray(res?.history) ? res.history : [];
      const list =
        typeof normalizeHistoryKeywords === 'function'
          ? await normalizeHistoryKeywords(rawList)
          : rawList;
      setHistoryKeywords(list);
      const nextSelectedKey = resolveHistoryKey(list, selectedHistoryKey);
      if (nextSelectedKey !== String(selectedHistoryKey || '')) setSelectedHistoryKey(nextSelectedKey);
      return list;
    } catch (e) {
      setHistoryError(e?.message || keywordsErrorMessage);
      setHistoryKeywords([]);
      return [];
    } finally {
      setHistoryLoading(false);
    }
  }, [keywordsErrorMessage, manager, normalizeHistoryKeywords, selectedHistoryKey]);

  const loadHistoryItems = useCallback(
    async (historyKey = selectedHistoryKey) => {
      if (!historyKey) {
        setHistoryPayload(null);
        return null;
      }
      setHistoryItemsLoading(true);
      setHistoryError('');
      try {
        const payload = await manager.getHistoryByKeyword(historyKey);
        setHistoryPayload(payload);
        return payload;
      } catch (e) {
        setHistoryError(e?.message || itemsErrorMessage);
        setHistoryPayload(null);
        return null;
      } finally {
        setHistoryItemsLoading(false);
      }
    },
    [itemsErrorMessage, manager, selectedHistoryKey]
  );

  const clearHistoryPayload = useCallback(() => {
    setHistoryPayload(null);
  }, []);

  return {
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
  };
}
